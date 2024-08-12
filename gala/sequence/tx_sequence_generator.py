from gala.graph import ICFG, ICFGNode, Permission, SlicedPath, Requirement, SlicedGraph
from slither.core.variables import StateVariable
from typing import Dict, List, Tuple, FrozenSet, Set, TypeAlias, Union
from .transaction import Transaction, TxSequence

TxSeqGenerationResult: TypeAlias = Dict[FrozenSet[ICFGNode], Dict[SlicedPath, Tuple[Set[TxSequence], List[ICFGNode]]]]


class TxSequenceGenerator:
    def __init__(self):
        pass

    def generate(self, sliced_icfg: SlicedGraph) -> TxSeqGenerationResult:
        # 整体逻辑
        # 目标：生成交易序列来绕过Requirement检查，从而trigger目标Permission
        # 约束：TX Sequences按照以下约束进行排序/Tx Sequence之间应遵循的Happens-Before关系进行排序
        # 1.目标Permission所在的Tx一定是最后一个Tx（基本原则）
        # 2.如果到达perm的Tx1路径上的Requirement依赖于SV1（读），则对该SV1进行写操作的Tx2应先于Tx2发生（读写依赖原则）
        # 3.如果对该SV1进行写操作路径上的Requirement依赖于SV2，则对该SV2进行写操作的Tx3应先于Tx2发生（传递性原则）
        # 4.如果对SV1进行写操作的右值集（污点分析得到的集合）包含SV3，则对SV3进行写操作的Tx4应该先于Tx2发生

        # 对每一个Perm进行遍历，逐一生成Tx sequence
        # FrozenSet[TxSequence]: 所有可以trigger permission list的交易序列集合
        # List[ICFGNode]：permission node list
        GeneratedTxSequences: TxSeqGenerationResult = dict()
        for perm_node, all_trigger_perm_node_slice_paths in sliced_icfg.perm_node_slice_map.items():
            # 每一个Perm，以及每一个Trigger该Perm的SlicePath
            for base_path, perm_req_nodes in all_trigger_perm_node_slice_paths.items():
                # 必须req node与base_path是同时相同的，才无需重新分析 ✅
                frozen_req_nodes: FrozenSet[ICFGNode] = frozenset(perm_req_nodes)
                base_path_map = GeneratedTxSequences.setdefault(frozen_req_nodes, {})
                if base_path in base_path_map:
                    base_path_map[base_path][1].append(perm_node)
                else:
                    TxSeqSet = self.generate_one_perm_node_tx_sequence(sliced_icfg, base_path, perm_req_nodes)
                    base_path_map[base_path] = (TxSeqSet, [perm_node])
        return GeneratedTxSequences

    def generate_one_perm_node_tx_sequence(self, sliced_icfg: SlicedGraph, base_path: SlicedPath, perm_req_nodes: List[ICFGNode]) -> Set[TxSequence]:
        # base_path:trigger目标perm_node的执行路径，位于最后一个Tx
        # Read-Write Dependency Analysis
        # 1. 获取所req节点关联的State Variable
        icfg = sliced_icfg.icfg
        # perm_req_nodes_state_var_dependent: Set[StateVariable] = self.get_req_nodes_dependent_state_vars(
        #     sliced_icfg.icfg, base_path, perm_req_nodes)

        # 情况1: 当前perm node 不受到任何req nodes的约束
        if len(perm_req_nodes) == 0:
            return {TxSequence(txs=[Transaction(base_path)])}

        # 有一些变量是仅在构造函数/变量声明阶段初始化一次，后续函数不修改这些state variable的值（constant/immutable）
        # 我们认为这些变量是已经被处理过的
        state_vars_processed: Set[StateVariable] = self.get_immutable_state_var_with_init_value(sliced_icfg)

        perm_req_nodes_dependent_state_vars: List[StateVariable] = list()
        for req_node in perm_req_nodes:
            req: Requirement = icfg.graph.nodes[req_node]["requirement"]
            for dependent_state_var in req.taint_result[base_path].state_vars_flow_to_sink:
                if (dependent_state_var in state_vars_processed) or (dependent_state_var in perm_req_nodes_dependent_state_vars):
                    continue
                perm_req_nodes_dependent_state_vars.append(dependent_state_var)

        # 情况2: 当前perm node的req约束和state variable的无关
        if len(perm_req_nodes_dependent_state_vars) == 0:
            return {TxSequence(txs=[Transaction(base_path)])}

        # 对依赖的perm_req_nodes_dependent_state_vars进行过滤：
        # 有一些state var在变量声明/构造函数初始化阶段仅初始化了一次（constant/immutable），外部用户无法更改
        # 对这些state variable进行过滤

        # 2.初始化Tx Seq
        all_tx_sequence: Set[TxSequence] = set()

        # 由于我们收集req时，最先check的req位于数组最前面，对dependent state var反向排序，逐个出栈，作为处理sv的次序
        first_state_var = perm_req_nodes_dependent_state_vars[0]

        # 3.查询第一个SV所有可能被写的路径，将这些SlicePath作为Tx加入到work_list中
        work_list: List[
            Tuple[SlicedPath, ICFGNode, StateVariable, TxSequence, List[StateVariable], Set[StateVariable]]] = []

        # 向第一个SV进行写操作的Slice
        write_first_sv_slices: List[Tuple[ICFGNode, SlicedPath]] = self.get_candidate_slices(sliced_icfg, first_state_var)
        for write_first_sv_node_and_slice in write_first_sv_slices:
            work_list.append(
                (write_first_sv_node_and_slice[1],  # working_slice
                 write_first_sv_node_and_slice[0],  # write_state_var_node
                 first_state_var,  # state_var_written
                 TxSequence(txs=[Transaction(base_path)]),  # working_tx_sequence
                 list(reversed(perm_req_nodes_dependent_state_vars)),  # state_vars_process_in_order
                 state_vars_processed.copy()))  # state_vars_processed

        # 4.外部大循环，生成Tx Seq
        while len(work_list) > 0:
            (working_slice, write_state_var_node, state_var_written, working_tx_sequence,
             state_vars_process_in_order, state_vars_processed) = work_list.pop()

            # 剪枝操作：无需添加到总交易列表中
            # 1.先判断当前Slice是否被重复
            if any(map(lambda added_tx: added_tx.exec_path == working_slice, working_tx_sequence.txs)):
                continue

            # 2.判断当前Slice是否比已经添加的Slice具有更强或者相同的约束条件
            working_slice_depend_svs = self.get_reqs_depend_state_vars(icfg, working_slice, working_slice.req_nodes)
            has_stronger_reqs: bool = False
            for added_tx in working_tx_sequence.txs:
                tx_exec_path: SlicedPath = added_tx.exec_path
                added_slice_depend_svs = self.get_reqs_depend_state_vars(icfg, tx_exec_path, tx_exec_path.req_nodes)
                # 如果所有的已经添加的slice依赖的sv都包含于working_slice所依赖的sv，说明working_slice_depend_svs具有更强的条件
                if all(map(lambda added_slice_depend_sv: added_slice_depend_sv in working_slice_depend_svs, added_slice_depend_svs)):
                    has_stronger_reqs = True
            if has_stronger_reqs:
                continue

            # 3.尝试向交易序列添加Slice，检查是否添加成功
            add_tx_success = working_tx_sequence.add_happens_before_tx(Transaction(working_slice))
            if not add_tx_success:
                continue

            # 4.检查约束3和约束4的条件是否被满足
            # dependent_state_vars_not_processed：约束3和约束4中所有未处理的状态变量集合
            dependent_state_vars_not_processed: Set[StateVariable] = set()
            # 检查约束3: 到达write node的所有的requirement节点
            write_node_reqs: List[ICFGNode] = sliced_icfg.perm_node_slice_map[write_state_var_node][working_slice]
            # 获取这些req_node依赖的state_variables,判断哪些State Variable没有被处理
            # 如果没有被写入，那么我们向状态变量处理序列添加这些状态
            write_node_req_dependent_svs = self.get_reqs_depend_state_vars(icfg, working_slice, write_node_reqs)

            for wnrdsv in write_node_req_dependent_svs:
                if wnrdsv not in state_vars_processed:
                    # 添加这些未处理状态
                    dependent_state_vars_not_processed.add(wnrdsv)

            # 检查约束4: write op的右值包含另外一个state variable，添加未处理的状态
            perm: Permission = sliced_icfg.icfg.graph.nodes[write_state_var_node]["permission"]
            write_node_rvalues = perm.state_var_write_taint_result[working_slice]
            state_vars_flow_to_write_node = write_node_rvalues.state_vars_flow_to_sink
            for svftwn in state_vars_flow_to_write_node:
                if svftwn not in state_vars_processed:
                    # 添加未处理的状态
                    dependent_state_vars_not_processed.add(svftwn)

            if len(dependent_state_vars_not_processed) == 0:
                # 如果约束都满足,说明当前Slice可以成功执行
                # 该Slice路径上对State Var的写操作都可以执行，这些State Variable得到处理
                state_vars_write_in_slice = self.get_all_state_vars_write_in_slice(icfg, working_slice)
                # 将当前Slice路径上写入的变量加入到已经处理的集合中
                state_vars_processed.update(state_vars_write_in_slice)
                # 将这些已修改的状态变量从需要处理的状态变量中移除
                state_vars_process_in_order = list(
                    filter(lambda sv_to_process: sv_to_process not in state_vars_processed,
                           state_vars_process_in_order))
            else:
                # 添加下一步要迭代处理的State Variable
                for dsvnp in dependent_state_vars_not_processed:
                    state_vars_process_in_order.append(dsvnp)

            # 一旦发现state_vars_process_ordered为空了，说明当前交易序列可以处理完成所有依赖的状态变量
            # 将该交易序列保存
            if len(state_vars_process_in_order) == 0:
                all_tx_sequence.add(working_tx_sequence.copy())
            # 检查state_vars_process_ordered栈顶元素，确定下一个可能的交易序列集合
            else:
                # 在constructor函数中有些状态变量已经被写，且只被写了一次，state_var_write_slice_map
                next_state_var_to_process = state_vars_process_in_order[len(state_vars_process_in_order) - 1]
                next_slices: List[Tuple[ICFGNode, SlicedPath]] = self.get_candidate_slices(sliced_icfg, next_state_var_to_process)
                # 逐个添加next slice，进行下一轮迭代
                for next_node_and_slice in next_slices:
                    next_node: ICFGNode = next_node_and_slice[0]
                    next_slice = next_node_and_slice[1]
                    work_list.append((next_slice,
                                      next_node,
                                      next_state_var_to_process,
                                      working_tx_sequence.copy(),
                                      state_vars_process_in_order.copy(),
                                      state_vars_processed.copy()))

        return all_tx_sequence

    @staticmethod
    def get_candidate_slices(sliced_icfg: SlicedGraph, state_var_dependent: StateVariable) -> List[Tuple[ICFGNode, SlicedPath]]:
        candidate_slices: List[Tuple[ICFGNode, SlicedPath]] = []
        if state_var_dependent in sliced_icfg.state_var_write_slice_map:
            write_sv_slices: Dict[ICFGNode, List[SlicedPath]] = sliced_icfg.state_var_write_slice_map[state_var_dependent]
            for write_node, write_slices in write_sv_slices.items():
                for write_slice in write_slices:
                    candidate_slices.append((write_node, write_slice))
        return candidate_slices

    @staticmethod
    def get_reqs_depend_state_vars(icfg: ICFG, slice: SlicedPath, req_nodes: List[ICFGNode]) -> Set[StateVariable]:
        dependent_state_vars: Set[StateVariable] = set()
        for node in req_nodes:
            req: Requirement = icfg.graph.nodes[node]["requirement"]
            if req.taint_result[slice]:
                for svfts in req.taint_result[slice].state_vars_flow_to_sink:
                    dependent_state_vars.add(svfts)
        return dependent_state_vars

    @staticmethod
    def get_all_state_vars_write_in_slice(icfg: ICFG, slice: SlicedPath) -> Set[StateVariable]:
        modify_state_vars: Set[StateVariable] = set()
        for node in slice.sv_write_nodes:
            perm: Permission = icfg.graph.nodes[node]["permission"]
            if perm.state_var_write:
                modify_state_vars.add(perm.state_var_write)
        return modify_state_vars

    @staticmethod
    def get_immutable_state_var_with_init_value(slice_graph: SlicedGraph) -> Set[StateVariable]:
        immutable_state_vars_with_init_value: Set[StateVariable] = set()
        for init_sv in slice_graph.icfg.sv_with_init_value:
            if init_sv not in slice_graph.state_var_write_slice_map.keys():
                immutable_state_vars_with_init_value.add(init_sv)
        return immutable_state_vars_with_init_value
