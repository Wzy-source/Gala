from .icfg import SSAIRNode
from typing import Set
from enum import auto, Enum
from slither.core.variables import StateVariable, LocalVariable
from slither.core.declarations import SolidityVariableComposed
from slither.slithir.operations import SolidityCall, Condition
from slither.core.declarations import Function
from typing import Optional, Set, Dict
from .sliced_graph import SlicedPath


class RequirementTaintResult:
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


class RequirementType(Enum):
    REQUIRE = auto()
    ASSERT = auto()
    IF = auto()


class Requirement:
    def __init__(self, requirement_type: RequirementType, node: SSAIRNode):
        self.node: SSAIRNode = node
        self.type: RequirementType = requirement_type
        self.taint_result: Dict[SlicedPath, RequirementTaintResult] = dict()

    def __str__(self) -> str:
        return f"Type: {self.type}, Node: {self.node}, Taint: {self.taint_result}"

    @staticmethod
    def extract_requirement_info(node: SSAIRNode) -> Optional['Requirement']:
        origin = node.node
        if origin.contains_require_or_assert():
            if isinstance(node, SolidityCall):
                if node.function.name in ["require(bool)", "require(bool,string)"]:
                    return Requirement(RequirementType.REQUIRE, node)
                elif node.function.name == "assert(bool)":
                    return Requirement(RequirementType.ASSERT, node)
        elif origin.contains_if(False):  # 不包含IF_Loop
            if isinstance(node, Condition):
                return Requirement(RequirementType.IF, node)
