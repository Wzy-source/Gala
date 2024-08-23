from typing import Optional, List, Tuple, Set, Dict
from .icfg import SSAIRNode, ICFGNode
from slither.core.declarations import SolidityVariableComposed
from slither.slithir.variables import ReferenceVariableSSA, StateIRVariable
from slither.core.variables import StateVariable, LocalVariable
from slither.slithir.operations import Assignment
from .sliced_graph import SlicedPath


class StateWriteTaintResult:
    def __init__(self, taint_states: Set[StateVariable], taint_params: Set[LocalVariable],
                 solidity_vars: Set[SolidityVariableComposed]):
        self.state_vars_flow_to_sink = taint_states
        self.params_flow_to_sink = taint_params
        self.solidity_vars_flow_to_sink = solidity_vars  # msg.sender

    def __str__(self):
        return f"""
            Taint State Variables: {' '.join(map(str, self.state_vars_flow_to_sink))},\n
            Taint Parameters: {' '.join(map(str, self.params_flow_to_sink))}.
        """


class StateWrite:
    def __init__(self, node: SSAIRNode, modified_state_var: StateVariable):
        self.node: SSAIRNode = node
        self.state_var_write: StateVariable = modified_state_var
        self.state_var_write_taint_result: Dict[SlicedPath, StateWriteTaintResult] = dict()

    def __str__(self) -> str:
        return f"Node: {str(self.node)}"

    @staticmethod
    def extract_state_write_info(ir_node: SSAIRNode) -> Optional['StateWrite']:
        # 写存储 TODO 是否可以考虑使用lvalue来判断值是否被写，而不是根据Op类型来判断
        #  elif isinstance(working_node,Binary): # Slither Bug: += / -= / *= 会解析为binary类型
        state_var = None
        if isinstance(ir_node, Assignment):
            variable_written = ir_node.lvalue
            if isinstance(variable_written, StateIRVariable):  # 直接写存储
                state_var = variable_written.non_ssa_version
            elif isinstance(variable_written, ReferenceVariableSSA):  # 通过引用写存储
                point_to = variable_written.points_to_origin
                if isinstance(point_to, StateIRVariable):
                    state_var = point_to.non_ssa_version

        if state_var is not None:
            return StateWrite(ir_node, state_var)
