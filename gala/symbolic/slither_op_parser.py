from z3 import Solver, sat, unsat, Z3Exception, unknown, Bool, Int, String, ExprRef, Or, Not, BitVecRef, And
from slither.slithir.operations import *
from slither.slithir.variables import *
from slither.core.variables import Variable
from typing import List, Dict, Union, TypeAlias
from .variable_extractor import Z3VariableExtractor
from .var_types import AllIRVarType, NonSSAVarType, ConstantWrapper
from gala.graph import EdgeType, SlicedPath
from gala.sequence import Transaction
from .symbolic_state import SymbolicState

# from .assignment import Assignment ✅
# from .binary import Binary, BinaryType ✅
# from .condition import Condition ✅
# from .high_level_call import HighLevelCall ✅
# from .index import Index ❌
# from .internal_call import InternalCall ✅
# from .library_call import LibraryCall ✅
# from .low_level_call import LowLevelCall ✅
# from .member import Member ❌
# from .return_operation import Return ✅
# from .send import Send ❌
# from .solidity_call import SolidityCall ✅
# from .transfer import Transfer ❌
# from .type_conversion import TypeConversion ✅
# from .unary import Unary, UnaryType ✅
# from .unpack import Unpack ✅
# from .length import Length ✅
# from .phi import Phi ✅
# from .nop import Nop ✅


FunctionCall: TypeAlias = Union[LibraryCall, HighLevelCall, EventCall, LowLevelCall, InternalCall, InternalDynamicCall]


class SlitherOpParser:
    def __init__(self, z3_solver: Solver):
        self.solver: Solver = z3_solver
        self.op_parsers: Dict = self.register_parsers()

    def register_parsers(self) -> Dict:
        return {
            Assignment: self.parse_assignment,
            TypeConversion: self.parse_type_conversion,
            SolidityCall: self.parse_solidity_call,
            Binary: self.parse_binary,
            Condition: self.parse_condition,
            Return: self.parse_return,
            Phi: self.parse_phi,
            Unary: self.parse_unary,
            Index: self.parse_index,
            Member: self.parse_member,
            FunctionCall: self.parse_function_call,
            Length: self.parse_length
        }

    def parse_tx_ops(self, state: SymbolicState):
        # 处理Slither指令的调用序列
        for op in state.tx.exec_path.ops:
            # 获取OP对应的Type
            parser = self.op_parsers.get(type(op))
            # 根据parser类型，处理对应程序
            if parser:
                parser(op, state)
            else:
                print("unhandled op type:", type(op), "op:", op)

    # ================================== Processors ==================================

    def parse_assignment(self, op: Assignment, state: SymbolicState):
        sym_lvalue = state.get_symbolic_var(op.lvalue)
        sym_rvalue = state.get_symbolic_var(op.rvalue)
        self.solver.add(sym_lvalue == sym_rvalue)

    def parse_length(self, op: Assignment, state: SymbolicState):
        # Trade-off：对于Length操作，并不精确的表示数组的长度，而是粗略地生成一个长度大于等于0的整数值即可
        sym_lvalue = state.get_symbolic_var(op.lvalue)
        self.solver.add(sym_lvalue >= 0)

    def parse_function_call(self, op: FunctionCall, state: SymbolicState):
        if op.lvalue is not None and op in state.tx.exec_path.call_nodes:
            sym_lvalue = state.get_symbolic_var(op.lvalue)
            # 使用栈来记录return destination
            state.call_stack.append(sym_lvalue)

    def parse_type_conversion(self, op: TypeConversion, state: SymbolicState):
        # 根据转换的类型，直接创建一个新的变量
        sym_lvalue = state.get_symbolic_var(op.lvalue)
        sym_src_value = state.get_symbolic_var(op.variable)  # TODO debug
        if type(sym_lvalue) == type(sym_src_value):
            self.solver.add(sym_lvalue == sym_src_value)

    def parse_solidity_call(self, op: SolidityCall, state: SymbolicState):
        if "require" in str(op) or "assert" in str(op):
            arg = op.arguments[0]
            z3_var = state.get_symbolic_var(arg)
            self.solver.add(z3_var == True)

    def parse_binary(self, op: Binary, state: SymbolicState) -> None:
        operator: BinaryType = op.type
        sym_lvalue = state.get_symbolic_var(op.lvalue)
        sym_rvalue0 = state.get_symbolic_var(op.variable_left)
        sym_rvalue1 = state.get_symbolic_var(op.variable_right)
        # According to the operator, parseing the three values.
        match operator:
            case BinaryType.EQUAL:
                self.solver.add(sym_lvalue == (sym_rvalue0 == sym_rvalue1))
            case BinaryType.NOT_EQUAL:
                self.solver.add(sym_lvalue == (sym_rvalue0 != sym_rvalue1))
            case BinaryType.GREATER:
                self.solver.add(sym_lvalue == (sym_rvalue0 > sym_rvalue1))
            case BinaryType.GREATER_EQUAL:
                self.solver.add(sym_lvalue == (sym_rvalue0 >= sym_rvalue1))
            case BinaryType.LESS:
                self.solver.add(sym_lvalue == (sym_rvalue0 < sym_rvalue1))
            case BinaryType.LESS_EQUAL:
                self.solver.add(sym_lvalue == (sym_rvalue0 <= sym_rvalue1))
            case BinaryType.ADDITION:
                self.solver.add(sym_lvalue == (sym_rvalue0 + sym_rvalue1))
            case BinaryType.MULTIPLICATION:
                self.solver.add(sym_lvalue == (sym_rvalue0 * sym_rvalue1))
            case BinaryType.SUBTRACTION:
                self.solver.add(sym_lvalue == (sym_rvalue0 - sym_rvalue1))
            case BinaryType.DIVISION:
                self.solver.add(sym_lvalue == (sym_rvalue0 / sym_rvalue1))
            case BinaryType.MODULO:
                self.solver.add(sym_lvalue == (sym_rvalue0 % sym_rvalue1))
            case BinaryType.POWER:
                self.solver.add(sym_lvalue == (sym_rvalue0 ** sym_rvalue1))
            case BinaryType.OR:
                self.solver.add(sym_lvalue == (sym_rvalue0 | sym_rvalue1))
            case BinaryType.AND:
                self.solver.add(sym_lvalue == (sym_rvalue0 & sym_rvalue1))
            case BinaryType.CARET:
                self.solver.add(sym_lvalue == (sym_rvalue0 ^ sym_rvalue1))
            case BinaryType.RIGHT_SHIFT:
                self.solver.add(sym_lvalue == (sym_rvalue0 >> sym_rvalue1))
            case BinaryType.LEFT_SHIFT:
                self.solver.add(sym_lvalue == (sym_rvalue0 << sym_rvalue1))
            case BinaryType.OROR:
                self.solver.add(sym_lvalue == Or(sym_rvalue0, sym_rvalue1))
            case BinaryType.ANDAND:
                self.solver.add(sym_lvalue == And(sym_rvalue0, sym_rvalue1))
            case _:
                raise Exception(f"Unknown Binary Operation: {operator}")

    def parse_condition(self, op: Condition, state: SymbolicState):
        edge_type: EdgeType = state.tx.exec_path.condition_node_edge_type_map[op]
        z3var = state.get_symbolic_var(op.read[0])
        if edge_type == EdgeType.IF_TRUE:
            self.solver.add(z3var == True)
        elif edge_type == EdgeType.IF_FALSE:
            self.solver.add(z3var == False)
        else:
            raise Exception(f"Unknown Condition Result: {str(edge_type)}, op: {str(op)}")

    def parse_return(self, op: Return, state: SymbolicState):
        returned_value = op.used[0]
        z3_return_var = state.get_symbolic_var(returned_value)
        # get the returning destination from the call stack
        if len(state.call_stack) > 0:
            z3_dst_var = state.call_stack.pop()
            # let the return_dst be equal to the current returned value.
            if type(z3_dst_var) == type(z3_return_var):
                self.solver.add(z3_dst_var == z3_return_var)

    def parse_phi(self, op: Phi, state: SymbolicState):
        lvalue: NonSSAVarType = self.convert_to_non_ssa_var(op.lvalue)
        rvalue_list: List[Variable] = []

        for rvalue in op.read:
            rvalue = self.convert_to_non_ssa_var(rvalue)
            if rvalue != lvalue and rvalue not in rvalue_list:
                rvalue_list.append(rvalue)

        if rvalue_list:
            # use a list to store the generated constraints
            constraints_list = []

            # The Z3 objs recorded or created from the lvalue
            sym_lvalue = state.get_symbolic_var(lvalue)

            for rvalue in rvalue_list:
                sym_rvalue = state.get_symbolic_var(rvalue)
                constraints_list.append(sym_rvalue == sym_lvalue)
            # OR relations
            self.solver.add(Or(constraints_list))

    def parse_unary(self, op: Unary, state: SymbolicState):
        # 一元操作
        sym_lvalue = state.get_symbolic_var(op.lvalue)
        sym_rvalue = state.get_symbolic_var(op.rvalue)
        if op.type == UnaryType.BANG:  # 非操作
            self.solver.add(sym_lvalue == Not(sym_rvalue))
        elif op.type == UnaryType.TILD:
            # Bitwise NOT
            if isinstance(sym_rvalue, BitVecRef):
                # Ensure the operand is treated as a bit-vector for bitwise operations
                self.solver.add(sym_lvalue == ~sym_rvalue)
            else:
                raise TypeError("Operand for bitwise NOT must be a BitVecRef")

        else:
            raise Exception(f"Unknown Unary Operation: {str(op.type)}, op: {str(op)}")

    def parse_index(self, op: Index, state: SymbolicState):
        return

    def parse_member(self, op: Member, state: SymbolicState):
        return

    # ================================== Utils ==================================

    @staticmethod
    def convert_to_non_ssa_var(var: Union[AllIRVarType, Variable]) -> NonSSAVarType:
        if hasattr(var, "non_ssa_version"):
            return var.non_ssa_version
        else:
            return var
