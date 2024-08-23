from slither.core.cfg.node import NodeType
from slither.core.declarations import Contract, Function, FunctionContract
from typing import List, Set, Tuple, Dict, Optional, Union
from slither.core.variables import StateVariable
from .requirement import Requirement
from .icfg import ICFGNode, ICFG, EdgeType, SlitherNode, SSAIRNode
from .state_write import StateWrite

from slither.slithir.operations import HighLevelCall, InternalCall, Assignment, LibraryCall


class ICFGBuilder:
    def __init__(self) -> None:
        pass

    def build(self, main_contract: Contract, program_points: Set[SSAIRNode]) -> ICFG:
        """
        遍历合约，收集节点和边，构造ICFG
        判断当前节点是否是Permission Node
        判断当前节点是否是Requirement Node
        如果是，则添加Permission Flag
        """
        icfg: ICFG = ICFG(main_contract)
        # 收集已初始化的全部sv
        # 1.变量声明时已经初始化的sv  2.构造函数中初始化的sv
        icfg.sv_with_init_value = set(filter(lambda sv: sv.initialized, main_contract.state_variables))
        if main_contract.constructor is not None:
            icfg.sv_with_init_value.union(set(main_contract.constructor.all_state_variables_written()))

        # 首先需要添加所有函数的节点，再添加边
        # 不能同时添加，应为在添加边的时候，有一些节点还未添加
        for fn in main_contract.functions_and_modifiers:  # 将modifier和函数同等看待
            # 这些函数不能被调用用户/函数调用
            if fn.is_receive or fn.is_fallback:
                continue
            if not fn.entry_point:
                continue
            # 记录当前函数读和写了哪些状态变量
            # self.collect_state_var_read_write_fn(icfg, fn)
            new_entry = self.mock_entry_point(icfg, fn.entry_point)  # 伪造一个统一的entry point
            # 将函数的入口节点（entry）添加到work_list中
            work_list: List[ICFGNode] = [new_entry]
            visited_list: Set[ICFGNode] = set()
            while len(work_list) > 0:
                cur_node = work_list.pop()
                if cur_node in visited_list:  # 如果已经访问过，则直接跳过
                    continue
                visited_list.add(cur_node)
                self.process_one_node(icfg, cur_node, fn, program_points)
                sons = cur_node.sons
                # 如果不存在孩子节点，说明已经到达最后的位置（不一定是return，也可能是revert等）
                # 将其与exit_point相连接，以便后续的遍历
                if len(sons) == 0:
                    exit_point = self.mock_exit_point(icfg, cur_node)
                    self.process_one_node(icfg, exit_point, fn, program_points)
                # 将子节点添加到work_list中进行下一轮迭代
                else:
                    for son in cur_node.sons:
                        work_list.append(son)

        # 添加所有节点的边
        visited_list: Set[ICFGNode] = set()
        for fn in main_contract.functions_and_modifiers:
            # 这些函数不能被调用用户/函数调用
            if fn.is_receive or fn.is_fallback:
                continue
            if not fn.entry_point:
                continue
            entry_point = icfg.func_entry_point_map[fn]
            work_list: List[ICFGNode] = [entry_point]
            while len(work_list) > 0:
                cur_node = work_list.pop()
                if cur_node in visited_list:
                    continue
                visited_list.add(cur_node)
                self.process_node_edges(icfg, cur_node)
                for son in cur_node.sons:
                    work_list.append(son)
        return icfg

    def process_one_node(self, icfg: ICFG, node: SlitherNode, func: Function, program_points: Set[SSAIRNode]) -> None:
        if self.has_ssa(node):
            for irn in node.irs_ssa:
                attr = self.gen_node_attr(func_scope=func, node=irn, program_points=program_points)
                # 判断当前Permission的类型是否为MODIFY_STATE，如果是则将当前节点和对应修改的state保存到icfg的一个索引数组中
                if attr["is_state_write_node"]:
                    modified_state = attr["state_write"].state_var_write
                    icfg.sv_write_fn_map.setdefault(modified_state, dict()).setdefault(node.function, set()).add(irn)

                # 将节点添加到图中，**attr用于展开字典参数
                icfg.graph.add_node(irn, **attr)
            # 添加边
            for index in range(len(node.irs_ssa) - 1):
                src_ir = node.irs_ssa[index]
                dst_ir = node.irs_ssa[index + 1]
                icfg.graph.add_edge(src_ir, dst_ir, **self.gen_edge_attr(edge_type=EdgeType.GENERAL))
        else:
            # 将节点添加到图中
            icfg.graph.add_node(node, **self.gen_node_attr(func_scope=func, node=node, program_points=program_points))

    def process_node_edges(self, icfg: ICFG, node: SlitherNode) -> None:
        self.process_control_flow_edges(icfg, node)
        self.process_call_edge(icfg, node)

    def process_control_flow_edges(self, icfg: ICFG, node: SlitherNode) -> None:
        if self.has_ssa(node):
            src_node: SSAIRNode = node.irs_ssa[-1]
        else:
            src_node: SlitherNode = node
        # IF
        if node.son_true is not None or node.son_false is not None:
            if self.has_ssa(node.son_true):
                dst_son_true: ICFGNode = node.son_true.irs_ssa[0]
            else:
                dst_son_true: ICFGNode = node.son_true

            if self.has_ssa(node.son_false):
                dst_son_false: ICFGNode = node.son_false.irs_ssa[0]
            else:
                dst_son_false: ICFGNode = node.son_false
            icfg.graph.add_edge(src_node, dst_son_true, **self.gen_edge_attr(edge_type=EdgeType.IF_TRUE))
            icfg.graph.add_edge(src_node, dst_son_false, **self.gen_edge_attr(edge_type=EdgeType.IF_FALSE))
        # General
        else:
            for son in node.sons:
                if self.has_ssa(son):
                    dst_node = son.irs_ssa[0]
                else:
                    dst_node = son
                icfg.graph.add_edge(src_node, dst_node, **self.gen_edge_attr(edge_type=EdgeType.GENERAL))

    def process_call_edge(self, icfg: ICFG, node: SlitherNode) -> None:
        if not self.has_ssa(node):
            return
        else:
            for ir in node.irs_ssa:
                # Contract is only possible for library call, which inherits from highlevelcall
                if isinstance(ir, Union[LibraryCall, InternalCall]):
                    caller_node = ir
                    called_fn = caller_node.function
                    if called_fn in icfg.func_entry_point_map:  # 有一些interface函数没有具体实现，不考虑
                        callee_entry = icfg.func_entry_point_map[called_fn]
                        # 添加函数调用边
                        # 由于Slither将Modifier Call纳入到了Function nodes中，我们需要对Modifier和Function Call进行区分
                        call_type = EdgeType.MODIFIER_CALL if caller_node.is_modifier_call else EdgeType.FUNCTION_CALL
                        # 向
                        # 添加函数调用节点
                        icfg.graph.add_edge(caller_node, callee_entry,
                                            **self.gen_edge_attr(edge_type=call_type))

    @staticmethod
    def mock_entry_point(icfg: ICFG, origin_entry: SlitherNode) -> SlitherNode:
        fn = origin_entry.function
        file_scope = origin_entry.file_scope
        new_entry = SlitherNode(NodeType.ENTRYPOINT, -1, fn, file_scope)
        origin_entry.add_father(new_entry)
        new_entry.add_son(origin_entry)
        new_entry.set_function(fn)
        icfg.func_entry_point_map[fn] = new_entry  # 添加记录
        return new_entry

    @staticmethod
    def mock_exit_point(icfg: ICFG, origin_exit: SlitherNode) -> SlitherNode:
        fn = origin_exit.function
        file_scope = origin_exit.file_scope
        if fn not in icfg.func_exit_point_map.keys():
            # 由于Slither的设计，仅当函数最后有return语句，才有return节点
            # 我们对每一个函数执行结束的位置均添加了一个RETURN类型的节点进行标识
            # 因此可能存在一条路径有两个连续的Return节点=> 因此后续我们不能把Return类型的节点认为是ICFG中函数的结束位置
            new_exit = SlitherNode(NodeType.RETURN, -2, fn, file_scope)
            new_exit.set_function(fn)
            icfg.func_exit_point_map[fn] = new_exit
        else:
            new_exit = icfg.func_exit_point_map[fn]
        new_exit.add_father(origin_exit)
        origin_exit.add_son(new_exit)
        return new_exit

    @staticmethod
    def gen_node_attr(func_scope: Function, node: ICFGNode, program_points: Set[SSAIRNode]) -> Dict:
        # permission = None
        requirement = None
        state_write_info = None
        is_program_point = False
        if isinstance(node, SSAIRNode):
            # permission = Permission.extract_permission_info(node)
            state_write_info = StateWrite.extract_state_write_info(node)
            requirement = Requirement.extract_requirement_info(node)
            is_program_point = node in program_points
        return {
            "func_scope": func_scope,
            "is_requirement_node": requirement is not None,
            # "is_permission_node": permission is not None,
            "is_state_write_node": state_write_info is not None,
            "is_program_point": is_program_point,
            "requirement": requirement,
            # "permission": permission,
            "state_write": state_write_info
        }

    @staticmethod
    def gen_edge_attr(edge_type: EdgeType) -> Dict:
        return {
            "edge_type": edge_type
        }

    @staticmethod
    def has_ssa(node: SlitherNode) -> bool:
        return len(node.irs_ssa) > 0
