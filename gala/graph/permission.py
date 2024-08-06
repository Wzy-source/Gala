from enum import auto, Enum
from typing import Optional, List, Tuple, Set, Dict
from .icfg import SSAIRNode, ICFGNode
from slither.core.declarations import SolidityVariableComposed
from slither.slithir.variables import ReferenceVariableSSA, StateIRVariable
from slither.core.variables import StateVariable, LocalVariable
from slither.slithir.operations import Assignment
from .sliced_graph import SlicedPath


class PermissionType(Enum):  # TODO 补充类型
    MODIFY_STATE = auto()
    TRANSFER_MONEY = auto()
    SUICIDE = auto()
    UNSAFE_CALL = auto()
    DEPLOY_CONTRACT = auto()


class PermissionTaintResult:
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


class Permission:
    def __init__(self, permission_type: PermissionType, node: SSAIRNode,
                 modified_state_var: Optional[StateVariable] = None):
        self.type: PermissionType = permission_type
        self.node: SSAIRNode = node
        self.state_var_write: Optional[StateVariable] = modified_state_var
        self.state_var_write_taint_result: Dict[SlicedPath, PermissionTaintResult] = dict()

    def __str__(self) -> str:
        return f"Type: {self.type}, Node: {str(self.node)}"

    @property
    def get_type(self) -> PermissionType:
        return self.type

    @staticmethod
    def extract_permission_info(working_node: SSAIRNode) -> Optional['Permission']:
        """
        提取节点的Permission信息，判断是哪种Permission类型
        1. 转钱相关：Transfer、Send
        2. 函数调用相关：low-level call、delegate call
        3. suicide：selfdestruct
        4. 写存储：write state variable
        5. 部署合约：create/create2/new
        6. TODO 待完善和细化
        """
        # 写存储
        state_var = handle_state_variable_write_node(working_node)
        if state_var:
            return Permission(permission_type=PermissionType.MODIFY_STATE, node=working_node,
                              modified_state_var=state_var)


# 可以考虑将下面两个方法合并到Permission Extractor中，类似于ICFG和ICFG Builder的关系
def handle_state_variable_write_node(ir_node: SSAIRNode) -> Optional[StateVariable]:
    # 写存储 TODO 是否可以考虑使用lvalue来判断值是否被写，而不是根据Op类型来判断
    if isinstance(ir_node, Assignment):
        variable_written = ir_node.lvalue
        if isinstance(variable_written, StateIRVariable):  # 直接写存储
            return variable_written.non_ssa_version
        elif isinstance(variable_written, ReferenceVariableSSA):  # 通过引用写存储
            point_to = variable_written.points_to_origin
            if isinstance(point_to, StateIRVariable):
                return point_to.non_ssa_version

    #  elif isinstance(working_node,Binary): # Slither Bug: += / -= / *= 会解析为binary类型
