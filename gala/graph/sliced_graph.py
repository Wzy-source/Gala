from slither.core.declarations import Function
from typing import List, Dict, Set, Tuple
from .icfg import ICFGNode, ICFG, EdgeType
from slither.core.variables import StateVariable


class SlicedPath:
    def __init__(self, slice_func: Function, path: List[ICFGNode]):
        self.slice_func: Function = slice_func
        self.path: List[ICFGNode] = path
        self.req_nodes: List[ICFGNode] = []
        self.sv_write_nodes: List[ICFGNode] = []


class SlicedGraph:
    def __init__(self, icfg: ICFG):
        self.icfg: ICFG = icfg
        # 所有的执行路径切片,按照函数进行划分
        self.func_slices_map: Dict[Function, List[SlicedPath]] = {}
        # state_var_write_slice_map用于记录可以trigger state var被写的所有执行路径
        self.state_var_write_slice_map: Dict[StateVariable, Dict[ICFGNode, List[SlicedPath]]] = {}
        # perm_node_slice_map用于记录可以到达一个permission node的所有执行路径,以及到达perm_node的所有requirement节点
        self.perm_node_slice_map: Dict[ICFGNode, Dict[SlicedPath, List[ICFGNode]]] = {}
