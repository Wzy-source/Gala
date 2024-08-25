from slither.core.declarations import Contract
from slither.core.variables import StateVariable
from slither.slithir.variables import StateIRVariable, ReferenceVariableSSA, ReferenceVariable
from slither.slithir.operations import Operation, Transfer, Send, Assignment, SolidityCall
from typing import List, Set


class CrucialOpExplorer:
    def __init__(self):
        pass

    def explore(self, main_contract: Contract) -> Set[Operation]:
        crucial_ops: Set[Operation] = set()
        for fn in main_contract.functions:
            if fn.is_constructor or fn.is_fallback or fn.is_receive:
                continue
            for node in fn.nodes:
                if len(node.irs_ssa) == 0:
                    continue
                for op in node.irs_ssa:
                    # if self.is_ownership_transfer_op(op):
                    #     crucial_ops.add(op)
                    if self.is_state_var_write_op(op):
                        crucial_ops.add(op)
                    # if self.is_force_closed_op(op):
                    #     crucial_ops.add(op)
                    # elif self.is_transfer_money_op(op):
                    #     crucial_ops.add(op)
                    # elif self.is_suicide_op(op):
                    #     crucial_ops.add(op)
        return crucial_ops

    @staticmethod
    def is_ownership_transfer_op(op: Operation) -> bool:
        if isinstance(op, Assignment):
            lvalue = op.lvalue
            if isinstance(lvalue, StateVariable):
                if lvalue.name in ["owner", "ceo", "admin", "_owner", "_admin"] and str(lvalue.type) == "address":
                    return True
        return False

    @staticmethod
    def is_force_closed_op(op: Operation) -> bool:
        if isinstance(op, Assignment):
            lvalue = op.lvalue
            if hasattr(lvalue, "non_ssa_version"):
                lvalue = lvalue.non_ssa_version
            if isinstance(lvalue, ReferenceVariable):
                lvalue = lvalue.points_to_origin
            if isinstance(lvalue, StateVariable):
                if lvalue.name == "isForeclosed" and op.rvalue.name == "True" and op.node.function.name == "collectRentUser":
                    return True
        return False

    @staticmethod
    def is_transfer_money_op(op: Operation) -> bool:
        return isinstance(op, Transfer) or isinstance(op, Send)

    @staticmethod
    def is_state_var_write_op(op: Operation) -> bool:
        if isinstance(op, Assignment):
            variable_written = op.lvalue
            if isinstance(variable_written, StateIRVariable):  # 直接写存储
                return True
            elif isinstance(variable_written, ReferenceVariableSSA):  # 通过引用写存储
                point_to = variable_written.points_to_origin
                if isinstance(point_to, StateIRVariable):
                    return True

    @staticmethod
    def is_suicide_op(op: Operation) -> bool:
        if isinstance(op, SolidityCall):
            if op.function.name in ["selfdestruct(address)", "suicide(address)"]:
                return True
        return False

    @staticmethod
    def is_delegate_call_op(op: Operation) -> bool:
        # if isinstance(op, SolidityCall):
        #     if op.function.name == ""
        return False
