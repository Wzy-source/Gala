# 污点分析
from gala.graph import ICFG, ICFGNode, ICFGEdge, EdgeType, SlitherNode, SSAIRNode
from slither.core.declarations import FunctionContract, Function, SolidityVariableComposed, SolidityVariable
from slither.core.variables import StateVariable, LocalVariable
from slither.slithir.variables import StateIRVariable, LocalIRVariable, Constant
from slither.slithir.variables.variable import Variable
from slither.slithir.operations import InternalCall, HighLevelCall
from typing import Mapping, Set, List, Dict, FrozenSet, Tuple, TypeAlias
from gala.graph import Requirement, Permission, RequirementTaintResult
from .utils import is_eoa_callable_func, get_fun_params_in_taint_vars
from .edge_processor import EdgeProcessor, FlowDirection
from slither.slithir.operations import Assignment

""" TODO
1.constructor逻辑和state variable的初始化操作都是包含在内的，需要在Permission收集阶段过滤
2.在符号执行阶段，这些state variable的初始化值可以作为一种state
3.
"""

StateVarWriteTaintResult: TypeAlias = Dict[
    ICFGNode, List[Tuple[List[ICFGNode], List[StateVariable], List[LocalVariable], List[SolidityVariableComposed]]]]


class TaintAnalyzer:
    def __init__(self) -> None:
        pass

    def analyze(self, icfg: ICFG) -> Dict[StateVariable, StateVarWriteTaintResult]:
        # 更新约束节点的信息：
        # 1.通过后向污点分析，找到所有Tainted State Variables
        # 2.接着逐一对Requirement依赖的SV进行分析，发现SV所有可能被写入控制流
        # 更新权限节点的信息，找到所有Permission的约束集
        # perms_with_same_req_sequences = self.collect_requires_for_perms(icfg)
        graph = icfg.graph
        all_state_vars_write_seqs: Dict[StateVariable, StateVarWriteTaintResult] = dict()
        for node, attrs in graph.nodes(data=True):
            if not attrs["is_requirement_node"]:
                continue
            # 对于每一个requirement_node进行污点分析
            req: Requirement = attrs["requirement"]
            # 收集每一个require中的条件判断依赖于哪些变量
            self.collect_req_taint_variables(icfg, req)
            # 在每一个require node关联的variable知道后，可以发现有一些req关联的是state variable
            # 我们进一步分析这些state variable被写入的路径，以及通过污点分析，找到被写入的是哪些变量
            # 后续在构造交易时：
            # 比如被写入的是变量是param，说明是attacker controllable
            # 比如被写入的变量是另外一个state variable，说明需要迭代的找到修改另外一个state variable的函数
            self.collect_sv_write_node_rvalue(icfg, all_state_vars_write_seqs, req)
        return all_state_vars_write_seqs

    @staticmethod
    def collect_req_taint_variables(icfg: ICFG, req: Requirement) -> None:
        """
        将约束节点进行前向污点传播，找到依赖的State Variables 以及 Params
        """
        req_sink = req.node
        func_scope: Function = icfg.graph.nodes[req_sink]["func_scope"]
        sink_var = req_sink.read[0]  # TODO 判断正确性
        # 收集当前req的污点分析结果
        state_vars_flow_to_sink: Set[StateVariable] = set()
        params_flow_to_sink: Set[LocalVariable] = set()
        solidity_vars_flow_to_sink: Set[SolidityVariableComposed] = set()
        # 污点分析过程中的局部变量
        # param1: cur_node:当前分析的节点
        # param2: visited_nodes:已经访问过的节点
        # param3: tainted_var:用于污点传播
        work_list: List[Tuple[ICFGNode, List[ICFGNode], Set[Variable]]] = [(req_sink, list(), {sink_var})]
        while len(work_list) > 0:
            cur_node, visited_nodes, tainted_vars = work_list.pop()
            if cur_node in visited_nodes:
                continue
            else:
                visited_nodes.append(cur_node)
            # 到达entry point
            if cur_node == icfg.func_entry_point_map[func_scope]:
                continue

            # 对当前节点进行处理：记录对Variable进行写的操作（污点传播）
            # TODO 使用lvalue来判断值是否被写，而不是根据Op类型判断？
            if isinstance(cur_node, SSAIRNode) and hasattr(cur_node, "lvalue"):
                var_written = cur_node.lvalue
                # 判断这个变量是否包含在污点集合内
                if var_written in tainted_vars:
                    tainted_vars.remove(var_written)  # 删除已经被处理的变量
                    for new_taint_var in cur_node.read:
                        # 污点传播过程
                        # 常量、solidity var、param不参与污点传播（不会被赋值，即无法成为左值）
                        if isinstance(new_taint_var, Constant):
                            continue
                        elif isinstance(new_taint_var, SolidityVariableComposed):
                            solidity_vars_flow_to_sink.add(new_taint_var)
                            continue
                        elif isinstance(new_taint_var, LocalIRVariable):
                            if new_taint_var.non_ssa_version in func_scope.parameters:
                                # 判断是否是函数的参数,函数参数不参与污点传播
                                params_flow_to_sink.add(new_taint_var.non_ssa_version)
                                continue
                        # sv直接影响require的结果
                        elif isinstance(new_taint_var, StateIRVariable):
                            state_vars_flow_to_sink.add(new_taint_var.non_ssa_version)

                        # 对于其他类型的变量，将其加入到污点集合中
                        tainted_vars.add(new_taint_var)

            # 进行前驱节点的下一轮迭代
            control_flow_edge_types = [EdgeType.IF_FALSE, EdgeType.IF_TRUE, EdgeType.GENERAL]
            control_flow_in_edges = EdgeProcessor.get_edges_by_types(icfg.graph, cur_node, control_flow_edge_types,
                                                                     FlowDirection.BACKWARD)
            for edge in control_flow_in_edges:
                work_list.append((edge[0], visited_nodes.copy(), tainted_vars.copy()))
        # 所有的路径遍历完毕，将结果保存
        req.taint_result = RequirementTaintResult(taint_states=state_vars_flow_to_sink,
                                                  taint_params=params_flow_to_sink,
                                                  solidity_vars=solidity_vars_flow_to_sink)
        # 更新图中的requirement属性
        icfg.graph.nodes[req_sink]["requirement"] = req

    def collect_req_depend_sv_write_seq(self, icfg: ICFG, all_state_vars_write_seqs: Dict[
        StateVariable, StateVarWriteTaintResult], req: Requirement):

        req_depend_svs = req.taint_result.state_vars_flow_to_sink
        if len(req_depend_svs) == 0:  # 说明该require语句不依赖state variable，无需分析
            return
        for sv in req_depend_svs:
            # 已有state var被分析，直接跳过
            if sv in all_state_vars_write_seqs.keys():
                continue
            # 找到当前SV的所有写的位置,按照函数进行了划分
            sv_write_fns_dict = icfg.sv_write_fn_map[sv]
            # state_write_res 记录到达一个state variable被写入操作的所有控制流序列
            # key：ICFGNode 一个sv被写入的操作
            # value: List 执行到该“sv被写入的操作”的所有控制流序列
            state_write_res: StateVarWriteTaintResult = dict()
            for sv_write_nodes in sv_write_fns_dict.values():
                for svwn in sv_write_nodes:
                    res = self.propagate_one_sv_write(icfg, sv, svwn)
                    state_write_res[svwn] = res
            all_state_vars_write_seqs[sv] = state_write_res

    def propagate_one_sv_write(self, icfg: ICFG, state_var: StateVariable,
                               state_var_write_node: ICFGNode) -> List[
        Tuple[List[ICFGNode], List[StateVariable], List[LocalVariable], List[SolidityVariableComposed]]]:
        """
        对于每一个被写的sv的操作，前向传播，找到被写入的State Variable的控制流执行路径
        考虑函数调用与被调用,一直前向传播，直到传播到一个Callable函数的entry为止
        """
        graph = icfg.graph
        # 需要返回的结果
        state_var_write_taint_result: List[
            Tuple[List[ICFGNode], List[StateVariable], List[LocalVariable], List[SolidityVariableComposed]]] = []

        # 初始化一些在迭代过程中不断更新的变量
        # 用于污点传播
        # work_list控制外部大循环
        # 参数1: cur_node 当前正在分析的节点
        # 参数2: visited_nodes 在当前路径下已经访问的节点
        # 参数3: tainted_vars: 当前路径下被污染的变量，用于记录污点传播
        # 参数4: state_var_flow_to_write 在state_var_write_node中可能的右值（状态变量类型）
        # 参数5: params_flow_to_write 在state_var_write_node中可能的右值（参数类型）
        # 参数6: solidity_var_flow_to_write 在state_var_write_node中可能的右值（msg.sender等）
        work_list: List[Tuple[
            ICFGNode, List[ICFGNode], Set[Variable], List[StateVariable], List[LocalVariable], List[
                SolidityVariableComposed]]] = [
            (state_var_write_node, list(), {state_var}, list(), list(), list())]

        while len(work_list) > 0:
            cur_node, visited_nodes, tainted_vars, state_var_flow_to_write, params_flow_to_write, solidity_var_flow_to_write = work_list.pop()
            if cur_node in visited_nodes:
                continue
            else:
                visited_nodes.append(cur_node)

            # 到达Function Entry Point
            cur_func = graph.nodes[cur_node]["func_scope"]
            # 判断是否是外部账户可调用的函数
            is_eoa_callable_func(func=cur_func)
            # 如果函数是EOA Callable的（可以在交易中被调用，则停止迭代）
            if cur_node == icfg.func_entry_point_map[cur_func]:
                if is_eoa_callable_func(func=cur_func):
                    path = list(reversed(visited_nodes))
                    state_var_write_taint_result.append(
                        (path.copy(), state_var_flow_to_write.copy(), params_flow_to_write.copy(),
                         solidity_var_flow_to_write.copy()))
                    continue
                else:
                    # 如果是private函数，则说明其一定会被另外一个函数调用，查找调用当前函数的函数，然后继续进行前向传播
                    # 在传播至caller的call site之前，先检查被被污染的变量中是否包含函数的参数
                    # 如果包含参数（形参），就将实际的实参加入到污点集合中
                    # 这些实参可能来自于Attack Input / State Variable 所以需要被进一步分析
                    call_edge_type = [EdgeType.FUNCTION_CALL]
                    call_in_edges = EdgeProcessor.get_edges_by_types(graph, cur_node, call_edge_type,
                                                                     FlowDirection.BACKWARD)
                    for edge in call_in_edges:  # 当前函数的调用者
                        # 调用当前函数的节点，这将是我们接下来前向传播过程需要遍历的新函数
                        caller_node = edge[0]
                        tainted_params = get_fun_params_in_taint_vars(tainted_vars, cur_func)
                        # 获取到调用者的实参，然后将实参加入到污点集合中
                        tainted_vars.clear()
                        if len(tainted_params) > 0 and isinstance(caller_node, InternalCall):
                            # TODO 可能需要修改InternalCall函数，可能是其他类型，自定义一个!!!
                            for tainted_param in tainted_params:
                                param, param_index = tainted_param  # 形参和实参的索引相同
                                arg = caller_node.arguments[param_index]
                                self.analysis_rvalue_type_to_propagate_taint(cur_func, arg, tainted_vars,
                                                                             state_var_flow_to_write,
                                                                             params_flow_to_write,
                                                                             solidity_var_flow_to_write)

                        # 进一步向前遍历
                        work_list.append(
                            (caller_node, visited_nodes.copy(), tainted_vars.copy(), state_var_flow_to_write.copy(),
                             params_flow_to_write.copy(), solidity_var_flow_to_write.copy())
                        )
                    continue
            # 污点传播的过程
            if isinstance(cur_node, Assignment):
                var_written = cur_node.lvalue
                if var_written in tainted_vars:
                    tainted_vars.remove(var_written)
                for new_taint_var in cur_node.read:
                    # 污点传播过程：
                    # 常量、solidity var、param不参与污点传播
                    self.analysis_rvalue_type_to_propagate_taint(cur_func, new_taint_var, tainted_vars,
                                                                 state_var_flow_to_write, params_flow_to_write,
                                                                 solidity_var_flow_to_write)

            # 如果是正常的节点，继续前向遍历
            control_flow_edge_types = [EdgeType.IF_FALSE, EdgeType.IF_TRUE, EdgeType.GENERAL]
            control_flow_in_edges = EdgeProcessor.get_edges_by_types(graph, cur_node, control_flow_edge_types,
                                                                     FlowDirection.BACKWARD)
            for edge in control_flow_in_edges:
                work_list.append((edge[0], visited_nodes.copy(), tainted_vars.copy(), state_var_flow_to_write.copy(),
                                  params_flow_to_write.copy(), solidity_var_flow_to_write.copy()))

        return state_var_write_taint_result

    @staticmethod
    def analysis_rvalue_type_to_propagate_taint(cur_func: Function, rvalue: Variable, tainted_vars: Set[Variable],
                                                tainted_state_vars: List[StateVariable],
                                                tainted_params: List[LocalVariable],
                                                tainted_solidity_vars: List[SolidityVariableComposed]):
        if isinstance(rvalue, Constant):
            return
        if isinstance(rvalue, SolidityVariableComposed):
            tainted_solidity_vars.append(rvalue)
            return
        if isinstance(rvalue, LocalIRVariable):  # 判断是否是函数的参数
            if rvalue.non_ssa_version in cur_func.parameters:
                # 只有eoa可以调用的函数的参数才能加入到params_flow_to_write集合中 因为这些参数是attacker可以控制的
                # 对于eoa无法调用过的函数，需要函数形参加入到tainted_vars中
                # 在遍历至entry point时，相当于调用者的实参值（右值）流向了形参（左值），进一步前向污点传播
                if is_eoa_callable_func(func=cur_func):
                    tainted_params.append(rvalue.non_ssa_version)
                    return
        if isinstance(rvalue, StateIRVariable):
            tainted_state_vars.append(rvalue.non_ssa_version)
            tainted_vars.add(rvalue)
            return

        tainted_vars.add(rvalue)
