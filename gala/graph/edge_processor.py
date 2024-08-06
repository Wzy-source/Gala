from .icfg import ICFGNode, EdgeType, ICFGEdge, SSAIRNode
from networkx import MultiDiGraph, get_edge_attributes
from typing import List, TypeAlias, Optional, Tuple, Dict, Set
from enum import Enum, auto


class FlowDirection(Enum):
    FORWARD = auto()
    BACKWARD = auto()


class EdgeProcessor:
    def __init__(self):
        pass

    def get_edges_by_types(graph: MultiDiGraph, node: ICFGNode, edge_types: List[EdgeType], direction: FlowDirection) \
            -> List[ICFGEdge]:
        edges: List[ICFGEdge] = []
        if direction == FlowDirection.FORWARD:
            edges = graph.out_edges(nbunch=node, data=True)
        elif direction == FlowDirection.BACKWARD:
            edges = graph.in_edges(nbunch=node, data=True)
        # e[0]:src_node, e[1]:dst_node, e[2]:edge_attr
        return list(filter(lambda e: e[2]["edge_type"] in edge_types, edges))
