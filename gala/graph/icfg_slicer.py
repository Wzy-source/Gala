from slither.core.variables import StateVariable
from slither.core.cfg.node import NodeType
from typing import List, Dict, Set, Tuple
from .utils import is_eoa_callable_func
from .edge_processor import FlowDirection, EdgeProcessor
from .icfg import ICFGNode, ICFG, EdgeType, SlitherNode
from slither.slithir.operations import SolidityCall, Condition
from .sliced_graph import SlicedGraph, SlicedPath


class ICFGSlicer:
    def __init__(self):
        pass

    def slice(self, icfg: ICFG) -> SlicedGraph:
        # 对一个合约的每一个函数进行切片，一个函数的切片是当前函数的所有可行的执行路径
        # 用于模拟一个交易的执行流，因此仅对可以被eoa调用的函数进行切片
        sliced_graph: SlicedGraph = SlicedGraph(icfg)
        for func, func_entry in icfg.func_entry_point_map.items():
            if func.is_constructor:
                self.slice_one_func_paths(sliced_graph, func_entry)
            elif is_eoa_callable_func(func):
                self.slice_one_func_paths(sliced_graph, func_entry)
        return sliced_graph

    @staticmethod
    def slice_one_func_paths(sliced_graph: SlicedGraph, func_entry: ICFGNode) -> None:
        graph = sliced_graph.icfg.graph
        cur_func = graph.nodes[func_entry]["func_scope"]
        # 参数1:cur_node 当前正在处理的节点
        # 参数2:当前Slice路径上的节点（允许重复---上下文敏感的函数调用，但不允许成环）
        # 参数3:visited nodes：当前函数中已经访问的所有节点（仅在一个函数范围内，不允许控制流成环）
        # 参数4:当前路径上所有函数调用节点
        # 参数5:call stack 函数调用栈 记录了每一个函数的return site和已经访问的节点
        work_list: List[Tuple[ICFGNode, List[ICFGNode], List[ICFGNode], Set[ICFGNode], List[Tuple[ICFGNode, List[ICFGNode]]]]] = [
            (func_entry, list(), list(), set(), list())]

        while len(work_list) > 0:
            cur_node, slice_nodes, visited_nodes, call_nodes, call_stack = work_list.pop()
            if cur_node in visited_nodes:
                continue
            # print(cur_node)
            visited_nodes.append(cur_node)
            slice_nodes.append(cur_node)

            # 处理当前节点
            # 1.如果到达revert函数调用，则说明不是一条有效的执行路径，直接跳过循环
            # 2.如果到达throw节点，同样跳过循环
            if isinstance(cur_node, SolidityCall):
                if "revert" in cur_node.function.name:
                    continue
            elif isinstance(cur_node, SlitherNode):
                if cur_node.type == NodeType.THROW:
                    continue

            # 3.如果有Call Edge，先遍历被调用的函数，然后返回到调用点
            call_edge_types = [EdgeType.FUNCTION_CALL, EdgeType.MODIFIER_CALL]
            call_edges = EdgeProcessor.get_edges_by_types(graph, cur_node, call_edge_types, FlowDirection.FORWARD)
            if len(call_edges) > 0:  # 说明当前是函数调用节点
                assert len(call_edges) == 1  # 仅能有一个被调用的函数
                call_nodes.add(cur_node)  # 添加路径上收集到的call node
                dst_node = call_edges[0][1]
                return_site_node = cur_node
                # 将cur_node加入到callstack中，作为“return site”，
                # 将visited_node也加入到callstack，在栈恢复时恢复visited_node
                call_stack.append((return_site_node, visited_nodes.copy()))
                # 进入新函数，visited_node被清空
                work_list.append((dst_node, slice_nodes.copy(), list(), call_nodes.copy(), call_stack.copy()))

            else:
                # 如果不存在out_edge，则说明控制流节点
                # 存在两种情况：
                # 1.len callstack == 0 说明主函数执行完毕
                # 2.len callstack > 0 说明还没有返回主函数，出栈，返回执行点
                control_flow_edge_types = [EdgeType.IF_FALSE, EdgeType.IF_TRUE, EdgeType.GENERAL]
                control_flow_out_edges = EdgeProcessor.get_edges_by_types(graph, cur_node, control_flow_edge_types, FlowDirection.FORWARD)
                if len(control_flow_out_edges) == 0:
                    if len(call_stack) == 0:
                        # 执行完毕，保存最终结果
                        one_slice_path = SlicedPath(slice_func=cur_func, path=slice_nodes.copy())
                        # 将当前Path以及Path中遇到的perms对应的reqs逐一进行收集
                        req_nodes: List[ICFGNode] = list()
                        sv_write_nodes: List[ICFGNode] = list()
                        for sn_index in range(0, len(slice_nodes)):
                            sn: ICFGNode = slice_nodes[sn_index]
                            # 当前Slice上的该节点是需要reach的位置
                            if graph.nodes[sn]["is_program_point"]:
                                sliced_graph.program_point_slice_map.setdefault(sn, dict()).setdefault(one_slice_path, req_nodes.copy())

                            if graph.nodes[sn]["is_requirement_node"]:
                                req_nodes.append(sn)
                                # 如果是IF条件判断，判断当前路径是IF-TRUE还是IF-FALSE，进行记录
                                if sn.node.contains_if(False) and isinstance(sn, Condition):
                                    sn_next_node: ICFGNode = slice_nodes[sn_index + 1]
                                    edge_type: EdgeType = sliced_graph.icfg.graph.edges[sn, sn_next_node, 0]["edge_type"]
                                    one_slice_path.condition_node_edge_type_map[sn] = edge_type

                            if graph.nodes[sn]["is_state_write_node"]:
                                sv_write_nodes.append(sn)
                                # 保存State Write Node以及其路径下依赖的Req Nodes
                                state_written: StateVariable = graph.nodes[sn]["state_write"].state_var_write
                                (sliced_graph.state_var_write_slice_map.setdefault(state_written, dict()).setdefault(sn, dict()).
                                 setdefault(one_slice_path, req_nodes.copy()))

                            # elif graph.nodes[sn]["is_permission_node"]:
                            #     # 保存Permission Node以及当前路径下依赖的reqs
                            #     sliced_graph.perm_node_slice_map.setdefault(sn, dict()).setdefault(one_slice_path, req_nodes.copy())
                            #     perm_info: Permission = graph.nodes[sn]["permission"]
                            #     if perm_info.type == PermissionType.MODIFY_STATE:
                            #         sv_write_nodes.append(sn)
                            #         state_written = perm_info.state_var_write
                            #         (sliced_graph.state_var_write_slice_map.setdefault(state_written, dict()).setdefault(sn, list()).append(
                            #             one_slice_path))

                        # 将路径上的所有约束节点进行保存
                        one_slice_path.req_nodes = req_nodes.copy()
                        one_slice_path.sv_write_nodes = sv_write_nodes.copy()
                        one_slice_path.call_nodes = call_nodes.copy()
                        # 加入到SlicedGraph的Slice集合中
                        sliced_graph.func_slices_map.setdefault(func_entry.function, list()).append(one_slice_path)

                    else:
                        return_site_node, return_func_visited_nodes = call_stack.pop()
                        return_site_next_edges = EdgeProcessor.get_edges_by_types(graph, return_site_node,
                                                                                  control_flow_edge_types,
                                                                                  FlowDirection.FORWARD)

                        for next_edge in return_site_next_edges:
                            dst_node = next_edge[1]
                            # 将visited_node恢复
                            work_list.append((dst_node, slice_nodes.copy(), return_func_visited_nodes.copy(), call_nodes.copy(), call_stack.copy()))

                else:
                    # 一般性情况，进一步遍历子节点即可
                    # 特判：这里还需要考虑Modifier中有if {_} 的情况，这时如果一个分支是_,则说明另一个分支不能走
                    # First check if there is a PLACEHOLDER node in the control flow edges
                    # 判断是否有没有place_holder_edge
                    place_holder_edge = next(
                        (edge for edge in control_flow_out_edges if isinstance(edge[1], SlitherNode) and edge[1].type == NodeType.PLACEHOLDER), None)
                    if place_holder_edge:
                        dst_node = place_holder_edge[1]
                        work_list.append((dst_node, slice_nodes, visited_nodes, call_nodes, call_stack))
                    # 没有place holder edge，正常添加
                    else:
                        for edge in control_flow_out_edges:
                            dst_node = edge[1]
                            work_list.append((dst_node, slice_nodes.copy(), visited_nodes.copy(), call_nodes.copy(), call_stack.copy()))
