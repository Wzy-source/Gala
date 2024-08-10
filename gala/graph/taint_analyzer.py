from .sliced_graph import SlicedGraph, SlicedPath
from typing import Tuple, Dict, Set, List
from slither.core.declarations import Function, SolidityVariableComposed
from slither.core.variables import Variable, StateVariable, LocalVariable
from .icfg import ICFG, ICFGNode, ICFGEdge, EdgeType, SlitherNode, SSAIRNode
from slither.slithir.variables import StateIRVariable, LocalIRVariable, Constant
from .requirement import Requirement, RequirementTaintResult
from .permission import Permission, PermissionTaintResult


class TaintAnalyzer:
    def __init__(self) -> None:
        pass

    def analyze(self, sliced_graph: SlicedGraph) -> None:
        func_slices_map: Dict[Function, List[SlicedPath]] = sliced_graph.func_slices_map
        state_var_write_slice_map: Dict[
            StateVariable, Dict[ICFGNode, List[SlicedPath]]] = sliced_graph.state_var_write_slice_map
        # 分析每一条路径上requirement节点依赖的状态变量
        for func, slices in func_slices_map.items():
            for slice in slices:
                for req_node in slice.req_nodes:
                    self.collect_req_taint_variables_in_slice(sliced_graph, slice, req_node)

        # 分析每一条路径上state var write节点的右值来源（谁写了当前state var）
        for write_node_slices_map in state_var_write_slice_map.values():
            for write_node, write_slices in write_node_slices_map.items():
                for write_slice in write_slices:
                    self.collect_sv_write_node_rvalue(sliced_graph, write_slice, write_node)

    @staticmethod
    def collect_req_taint_variables_in_slice(sliced_graph: SlicedGraph, slice_path: SlicedPath,
                                             req_node: ICFGNode) -> None:
        # 从req节点处开始遍历
        req_node_index = slice_path.ops.index(req_node)

        # 污点传播过程收集的中间变量
        taint_vars: Set[Variable] = {req_node.read[0]}
        # 收集当前req的污点分析结果
        state_vars_flow_to_sink: Set[StateVariable] = set()
        params_flow_to_sink: Set[LocalVariable] = set()
        solidity_vars_flow_to_sink: Set[SolidityVariableComposed] = set()

        # 开始前向传播，直到遍历到entry_point
        for node_index in range(req_node_index, -1, -1):
            working_node = slice_path.ops[node_index]
            working_func: Function = sliced_graph.icfg.graph.nodes[working_node]["func_scope"]

            # 如果是首节点的情况,也就是eoa_callable_func entry point 保存最终结果
            if node_index == 0:
                req: Requirement = sliced_graph.icfg.graph.nodes[req_node]["requirement"]
                req.taint_result[slice_path] = RequirementTaintResult(taint_states=state_vars_flow_to_sink.copy(),
                                                                      taint_params=params_flow_to_sink.copy(),
                                                                      solidity_vars=solidity_vars_flow_to_sink.copy())
            # 到达非首节点的entry point的情况 清空taint vars，只保留被污染的函数参数
            # 由于Slither在被调用的函数逻辑中，会使用Phi指令，将函数的形参和实参关联起来（上下文不敏感）
            # 也就是说，在到达被调用函数entry point之前，会首先进行一次赋值：
            # {Phi} prams := φ([arg1.1,arg1.2],[arg2.1,arg2.2]) arg是所有调用该函数传入的实际参数
            # 按照现有逻辑，遍历到非首节点的entry point时刻，所有的被污染的实参已经在taint_var中了
            elif working_node == sliced_graph.icfg.func_entry_point_map[working_func]:
                continue
            # 记录对Variable进行写的操作（污点传播）
            elif hasattr(working_node, "lvalue"):
                var_written = working_node.lvalue
                # 判断这个变量是否包含在污点集合内
                if var_written in taint_vars:
                    taint_vars.remove(var_written)  # 删除已经被处理的变量
                    for new_taint_var in working_node.read:
                        # 污点传播过程
                        # 常量、solidity var、param不参与污点传播（不会被赋值，即无法成为左值）
                        if isinstance(new_taint_var, Constant):
                            continue
                        elif isinstance(new_taint_var, SolidityVariableComposed):
                            solidity_vars_flow_to_sink.add(new_taint_var)
                            continue
                        elif isinstance(new_taint_var, LocalIRVariable):
                            # 判断是否是caller函数的参数,函数参数不参与污点传播
                            if working_func == slice_path.slice_func:
                                if new_taint_var.non_ssa_version in working_func.parameters:
                                    params_flow_to_sink.add(new_taint_var.non_ssa_version)
                                    continue
                        # sv直接影响require的结果
                        elif isinstance(new_taint_var, StateIRVariable):
                            state_vars_flow_to_sink.add(new_taint_var.non_ssa_version)

                        # 对于其他类型的变量，将其加入到污点集合中
                        taint_vars.add(new_taint_var)

    @staticmethod
    def collect_sv_write_node_rvalue(sliced_graph: SlicedGraph, slice_path: SlicedPath, write_node: ICFGNode):
        # 对于每一个向sv写入的操作，寻找其写入操作的右值可能收到哪些变量影响

        # 从write_node的位置开始向前遍历
        write_node_index = slice_path.ops.index(write_node)
        # 污点传播过程的中间变量
        taint_vars: Set[Variable] = {write_node.read[0]}
        # 收集当前write_node的污点分析结果
        state_vars_flow_to_sink: Set[StateVariable] = set()
        params_flow_to_sink: Set[LocalVariable] = set()
        solidity_vars_flow_to_sink: Set[SolidityVariableComposed] = set()

        for node_index in range(write_node_index, -1, -1):
            working_node = slice_path.ops[node_index]
            working_func: Function = sliced_graph.icfg.graph.nodes[working_node]["func_scope"]

            # 如果是首节点的情况,也就是eoa_callable_func entry point 保存最终结果
            if node_index == 0:
                perm: Permission = sliced_graph.icfg.graph.nodes[write_node]["permission"]
                perm.state_var_write_taint_result[slice_path] = PermissionTaintResult(
                    taint_states=state_vars_flow_to_sink.copy(),
                    taint_params=params_flow_to_sink.copy(),
                    solidity_vars=solidity_vars_flow_to_sink.copy())
            # 到达非首节点的entry point的情况 清空taint vars，只保留被污染的函数参数
            # 由于Slither在被调用的函数逻辑中，会使用Phi指令，将函数的形参和实参关联起来（上下文不敏感）
            # 也就是说，在到达被调用函数entry point之前，会首先进行一次赋值：
            # {Phi} prams := φ([arg1.1,arg1.2],[arg2.1,arg2.2]) arg是所有调用该函数传入的实际参数
            # 按照现有逻辑，遍历到非首节点的entry point时刻，所有的被污染的实参已经在taint_var中了
            elif working_node == sliced_graph.icfg.func_entry_point_map[working_func]:
                continue
            # 记录对Variable进行写的操作（污点传播）
            elif hasattr(working_node, "lvalue"):
                var_written = working_node.lvalue
                # 判断这个变量是否包含在污点集合内
                if var_written in taint_vars:
                    taint_vars.remove(var_written)  # 删除已经被处理的变量
                    for new_taint_var in working_node.read:
                        # 污点传播过程
                        # 常量、solidity var、param不参与污点传播（不会被赋值，即无法成为左值）
                        if isinstance(new_taint_var, Constant):
                            continue
                        elif isinstance(new_taint_var, SolidityVariableComposed):
                            solidity_vars_flow_to_sink.add(new_taint_var)
                            continue
                        elif isinstance(new_taint_var, LocalIRVariable):
                            # 判断是否是caller函数的参数,函数参数不参与污点传播
                            if working_func == slice_path.slice_func:
                                if new_taint_var.non_ssa_version in working_func.parameters:
                                    params_flow_to_sink.add(new_taint_var.non_ssa_version)
                                    continue
                        # sv直接影响require的结果
                        elif isinstance(new_taint_var, StateIRVariable):
                            state_vars_flow_to_sink.add(new_taint_var.non_ssa_version)

                        # 对于其他类型的变量，将其加入到污点集合中
                        taint_vars.add(new_taint_var)
