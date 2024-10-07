from slither.core.declarations import Contract
from slither.core.solidity_types import ElementaryType
from slither.core.variables import StateVariable
from slither.slithir.variables import StateIRVariable, ReferenceVariableSSA, ReferenceVariable
from slither.slithir.operations import Operation, Transfer, Send, Assignment, SolidityCall, Binary, Condition
from typing import List, Set


class CrucialOpExplorer:
    def __init__(self):
        pass

    def explore(self, main_contract: Contract) -> Set[Operation]:
        state_var_write_ops: Set[Operation] = set()
        ownership_transfer_ops: Set[Operation] = set()
        conditional_ops: Set[Operation] = set()
        suicide_ops: Set[Operation] = set()
        for fn in main_contract.functions_and_modifiers:
            if fn.is_constructor or fn.is_fallback or fn.is_receive:
                continue
            for node in fn.nodes:
                if len(node.irs_ssa) == 0:
                    continue
                for op in node.irs_ssa:
                    if self.is_state_var_write_op(op):
                        state_var_write_ops.add(op)
                    if self.is_conditional_op(op):
                        conditional_ops.add(op)
                    if self.is_suicide_op(op):
                        suicide_ops.add(op)
                    if self.is_ownership_transfer_op(op):
                        ownership_transfer_ops.add(op)
        # 获取到所有ops，根据ABAC规则，对op进行筛选，将符合条件的op加入到critical_ops集合中
        # 情况一：控制流相关的状态变量被写
        cfsv_ops = self.get_control_flow_related_sv_write(state_var_write_ops, conditional_ops)
        # 情况二：状态变量被任意写（右值来自于函数参数）
        absv_ops = self.get_arbitrary_sv_write(state_var_write_ops, conditional_ops)
        # 情况三：selfdestruct
        reach_suicide_ops = suicide_ops
        # 情况四：ownership_transfer:
        reach_owner_transfer_ops = ownership_transfer_ops
        critical_ops = cfsv_ops.union(absv_ops).union(reach_suicide_ops).union(reach_owner_transfer_ops)
        return critical_ops

    @staticmethod
    def get_control_flow_related_sv_write(state_var_write_ops: Set[Operation], conditional_ops: Set[Operation]) -> Set[Operation]:
        # 有bug，将owner过滤掉了
        target_ops: Set[Operation] = set()
        # 查看所有condition_op依赖的state variable
        control_flow_related_state_var_read: Set[StateVariable] = set()
        for con_op in conditional_ops:
            origin = con_op.node
            state_vars_read = origin.state_variables_read
            for sv in state_vars_read:
                if isinstance(sv.type, ElementaryType):
                    control_flow_related_state_var_read.add(sv)
        # 遍历所有state var write op，查看被写的状态变量是否是与控制流相关的
        for sv_write_op in state_var_write_ops:
            if hasattr(sv_write_op, "lvalue"):
                variable_written = sv_write_op.lvalue
                if hasattr(variable_written, "points_to_origin"):
                    variable_written = variable_written.points_to_origin
                if hasattr(variable_written, "non_ssa_version"):
                    variable_written = variable_written.non_ssa_version
                if variable_written in control_flow_related_state_var_read:
                    target_ops.add(sv_write_op)
        return target_ops

    @staticmethod
    def get_arbitrary_sv_write(state_var_write_ops: Set[Operation], conditional_ops: Set[Operation]) -> Set[Operation]:
        target_ops: Set[Operation] = set()
        # 状态变量被参数修改，并且在该op所在的函数中，没有conditional语句对其进行约束
        for sv_write_op in state_var_write_ops:
            variable_written = sv_write_op.lvalue
            if hasattr(variable_written, "points_to_origin"):
                variable_written = variable_written.points_to_origin
            if hasattr(variable_written, "non_ssa_version"):
                variable_written = variable_written.non_ssa_version

            # 先限定左值为基本类型看看效果
            if not isinstance(variable_written.type, ElementaryType):
                continue

            origin = sv_write_op.node
            local_variable_read = origin.local_variables_read
            if len(local_variable_read) > 0:
                origin_func = origin.function
                origin_modifiers = origin_func.modifiers
                # 找到当前指令所在的函数以及函数modifier所包含的conditional ops
                prec_condition_ops: Set[Operation] = set()
                for con_op in conditional_ops:
                    con_origin_func = con_op.node.function
                    if con_origin_func in origin_modifiers or con_origin_func == origin_func:
                        prec_condition_ops.add(con_op)
                # 判断con_op是否对local_variable_read进行了约束，且是否对左值进行了约束
                if len(prec_condition_ops) == 0:
                    target_ops.add(sv_write_op)
        return target_ops

    @staticmethod
    def is_ownership_transfer_op(op: Operation) -> bool:
        if isinstance(op, Assignment):
            lvalue = op.lvalue
            if hasattr(lvalue, "non_ssa_version"):
                lvalue = lvalue.non_ssa_version
            if isinstance(lvalue, StateVariable):
                if lvalue.name in ["owner", "ceo", "admin", "_owner", "_admin", "ceoAddress", "coo", "cooAddress"] and str(lvalue.type) == "address":
                    return True
        return False

    # @staticmethod
    # def is_force_closed_op(op: Operation) -> bool:
    #     if isinstance(op, Assignment):
    #         lvalue = op.lvalue
    #         if hasattr(lvalue, "non_ssa_version"):
    #             lvalue = lvalue.non_ssa_version
    #         if isinstance(lvalue, ReferenceVariable):
    #             lvalue = lvalue.points_to_origin
    #         if isinstance(lvalue, StateVariable):
    #             if lvalue.name == "isForeclosed" and op.rvalue.name == "True" and op.node.function.name == "collectRentUser":
    #                 return True
    #     return False

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
        elif hasattr(op, "lvalue") and isinstance(op, Binary):
            variable_written = op.lvalue
            if isinstance(variable_written, StateIRVariable):  # 直接写存储
                return True
            elif isinstance(variable_written, ReferenceVariableSSA):  # 通过引用写存储
                point_to = variable_written.points_to_origin
                if isinstance(point_to, StateIRVariable):
                    return True
        return False

    @staticmethod
    def is_suicide_op(op: Operation) -> bool:
        if isinstance(op, SolidityCall):
            if op.function.name in ["selfdestruct(address)", "suicide(address)"]:
                return True
        return False

    @staticmethod
    def is_conditional_op(op: Operation) -> bool:
        if isinstance(op, SolidityCall):
            if op.function.name in ["require(bool)", "require(bool,string)", "assert(bool)"]:
                return True
        origin = op.node
        if origin.contains_if(False):
            if isinstance(op, Condition):
                return True
        return False
