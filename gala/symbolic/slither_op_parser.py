from z3 import Solver, sat, unsat, Z3Exception, unknown, Bool, Int, String, ExprRef, Or, Not, BitVecRef, And, BitVec, BitVecVal, BoolVal, String, \
    StringVal, Extract, Array, BitVecSort, Select
from slither.slithir.operations import *
from slither.slithir.variables import *
from slither.core.variables import Variable
from typing import List, Dict, Union, TypeAlias
from .variable_extractor import Z3VariableExtractor
from .var_types import AllIRVarType, NonSSAVarType, ConstantWrapper
from gala.graph import EdgeType, SlicedPath
from gala.sequence import Transaction
from .symbolic_state import SymbolicState
from slither.core.solidity_types import ElementaryType, ArrayType, MappingType, Type

# from .assignment import Assignment ✅
# from .binary import Binary, BinaryType ✅
# from .condition import Condition ✅
# from .high_level_call import HighLevelCall ✅
# from .index import Index ✅
# from .internal_call import InternalCall ✅
# from .library_call import LibraryCall ✅
# from .low_level_call import LowLevelCall ✅
# from .member import Member ❌
# from .return_operation import Return ✅
# from .send import Send ⚠️
# from .solidity_call import SolidityCall ✅
# from .transfer import Transfer ⚠️
# from .type_conversion import TypeConversion ✅
# from .unary import Unary, UnaryType ✅
# from .unpack import Unpack ❌
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
            Length: self.parse_length,
            Nop: self.parse_nop,
            LibraryCall: self.parse_function_call,
            HighLevelCall: self.parse_function_call,
            EventCall: self.parse_function_call,
            LowLevelCall: self.parse_function_call,
            InternalCall: self.parse_function_call,
            InternalDynamicCall: self.parse_function_call,
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
        # 获取右值的符号表达式 ✅
        sym_rvalue = state.get_or_create_default_symbolic_var(op.rvalue)
        # 将这个符号表达式关联到左值变量
        state.set_symbolic_var(op, op.lvalue, sym_rvalue)

    def parse_length(self, op: Assignment, state: SymbolicState):
        # Trade-off：对于Length操作，并不精确的表示数组的长度，而是粗略地生成一个长度大于等于0的整数值即可
        # ✅
        sym_lvalue = state.get_or_create_default_symbolic_var(op.lvalue)
        self.solver.add(sym_lvalue >= 0)

    def parse_solidity_call(self, op: SolidityCall, state: SymbolicState):
        # ✅
        if "require" in str(op) or "assert" in str(op):
            arg = op.arguments[0]
            sym_value = state.get_or_create_default_symbolic_var(arg)
            self.solver.add(sym_value == True)

    def parse_function_call(self, op: FunctionCall, state: SymbolicState):
        # ✅
        if hasattr(op, "lvalue") and op.lvalue is not None and op in state.tx.exec_path.call_nodes:
            # 使用栈来记录return node
            state.call_stack.append(op.lvalue)

    def parse_return(self, op: Return, state: SymbolicState):
        # ✅
        ret_value = op.used[0]
        sym_ret_value = state.get_or_create_default_symbolic_var(ret_value)
        # get the returning destination from the call stack
        if len(state.call_stack) > 0:
            dst_value = state.call_stack.pop()
            if type(ret_value) == type(dst_value):
                state.set_symbolic_var(op, dst_value, sym_ret_value)

    def parse_type_conversion(self, op: TypeConversion, state: SymbolicState):
        # 根据转换的类型，直接创建一个新的变量
        # ✅
        # 目标转换类型
        convert_type = op.type
        convert_variable = op.variable
        sym_convert_variable = state.get_or_create_default_symbolic_var(convert_variable)
        sym_res = None
        # 判断待转换的值是否为常量
        if isinstance(convert_variable, Constant):
            if isinstance(convert_type, ElementaryType):
                if str(convert_type).startswith("uint") or str(convert_type).startswith("int"):
                    sym_res = BitVecVal(convert_variable.value, convert_type.size)
                elif str(convert_type) == "address":
                    sym_res = BitVecVal(convert_variable, 256)
                elif str(convert_type) == "bool":
                    sym_res = BoolVal(bool(convert_variable))
                elif str(convert_type).startswith("bytes"):
                    sym_res = BitVecVal(convert_variable, convert_type.size)
                elif str(convert_type) == "string":
                    sym_res = StringVal(convert_variable)
        else:  # 被转换的是变量
            if isinstance(convert_type, ElementaryType):
                if str(convert_type).startswith("uint") or str(convert_type).startswith("int"):
                    sym_res = Extract(255, 0, sym_convert_variable)
                elif str(convert_type) == "address":
                    sym_res = Extract(255, 0, sym_convert_variable)
                elif str(convert_type) == "bool":
                    sym_res = (convert_variable != 0)
                elif str(convert_type) == "string":
                    sym_res = Array(convert_variable.name, BitVecSort(256), BitVecSort(8))

        # 更新符号状态
        if sym_res is not None:
            state.set_symbolic_var(op, op.lvalue, sym_res)
        else:
            print("Unhandled target type for conversion:", str(convert_type))

    def parse_binary(self, op: Binary, state: SymbolicState) -> None:
        # ✅
        sym_lvalue = None
        operator: BinaryType = op.type
        sym_rvalue0 = state.get_or_create_default_symbolic_var(op.variable_left)
        sym_rvalue1 = state.get_or_create_default_symbolic_var(op.variable_right)
        # According to the operator, parseing the three values.
        match operator:
            case BinaryType.EQUAL:
                sym_lvalue = (sym_rvalue0 == sym_rvalue1)
            case BinaryType.NOT_EQUAL:
                sym_lvalue = (sym_rvalue0 != sym_rvalue1)
            case BinaryType.GREATER:
                sym_lvalue = (sym_rvalue0 > sym_rvalue1)
            case BinaryType.GREATER_EQUAL:
                sym_lvalue = (sym_rvalue0 >= sym_rvalue1)
            case BinaryType.LESS:
                sym_lvalue = (sym_rvalue0 < sym_rvalue1)
            case BinaryType.LESS_EQUAL:
                sym_lvalue = (sym_rvalue0 <= sym_rvalue1)
            case BinaryType.ADDITION:
                sym_lvalue = (sym_rvalue0 + sym_rvalue1)
            case BinaryType.MULTIPLICATION:
                sym_lvalue = (sym_rvalue0 * sym_rvalue1)
            case BinaryType.SUBTRACTION:
                sym_lvalue = (sym_rvalue0 - sym_rvalue1)
            case BinaryType.DIVISION:
                sym_lvalue = (sym_rvalue0 / sym_rvalue1)
            case BinaryType.MODULO:
                sym_lvalue = (sym_rvalue0 % sym_rvalue1)
            case BinaryType.POWER:  # BitVecRef不支持pow
                pass
            case BinaryType.OR:
                sym_lvalue = (sym_rvalue0 | sym_rvalue1)
            case BinaryType.AND:
                sym_lvalue = (sym_rvalue0 & sym_rvalue1)
            case BinaryType.CARET:
                sym_lvalue = (sym_rvalue0 ^ sym_rvalue1)
            case BinaryType.RIGHT_SHIFT:
                sym_lvalue = (sym_rvalue0 >> sym_rvalue1)
            case BinaryType.LEFT_SHIFT:
                sym_lvalue = (sym_rvalue0 << sym_rvalue1)
            case BinaryType.OROR:
                sym_lvalue = Or(sym_rvalue0, sym_rvalue1)
            case BinaryType.ANDAND:
                sym_lvalue = And(sym_rvalue0, sym_rvalue1)
            case _:
                raise Exception(f"Unknown Binary Operation: {operator}")

        if sym_lvalue is not None:
            state.set_symbolic_var(op, op.lvalue, sym_lvalue)

    def parse_condition(self, op: Condition, state: SymbolicState):
        # ✅
        if op not in state.tx.exec_path.condition_node_edge_type_map.keys():
            return
        edge_type: EdgeType = state.tx.exec_path.condition_node_edge_type_map[op]
        sym_value = state.get_or_create_default_symbolic_var(op.read[0])
        if edge_type == EdgeType.IF_TRUE:
            self.solver.add(sym_value == True)
        elif edge_type == EdgeType.IF_FALSE:
            self.solver.add(sym_value == False)
        else:
            raise Exception(f"Unknown Condition Result: {str(edge_type)}, op: {str(op)}")

    def parse_phi(self, op: Phi, state: SymbolicState):
        # ✅
        rvalue_list: List[Variable] = []
        lvalue = op.lvalue
        for rvalue in op.read:
            rvalue = self.convert_to_non_ssa_var(rvalue)
            if rvalue != lvalue and rvalue not in rvalue_list and rvalue.type == lvalue.type:
                rvalue_list.append(rvalue)

        if rvalue_list:
            # use a list to store the generated constraints
            constraints_list = []

            # The Z3 objs recorded or created from the lvalue
            sym_lvalue = state.get_or_create_default_symbolic_var(lvalue)

            for rvalue in rvalue_list:
                sym_rvalue = state.get_or_create_default_symbolic_var(rvalue)
                constraints_list.append(sym_rvalue == sym_lvalue)
            # OR relations
            self.solver.add(Or(constraints_list))

    def parse_unary(self, op: Unary, state: SymbolicState):
        # 一元操作 ✅
        sym_rvalue = state.get_or_create_default_symbolic_var(op.rvalue)
        if op.type == UnaryType.BANG:  # 非操作
            sym_rvalue = Not(sym_rvalue)
        elif op.type == UnaryType.TILD:
            # Bitwise NOT
            if isinstance(sym_rvalue, BitVecRef):
                # Ensure the operand is treated as a bit-vector for bitwise operations
                sym_rvalue = ~sym_rvalue
            else:
                raise TypeError("Operand for bitwise NOT must be a BitVecRef")

        else:
            raise Exception(f"Unknown Unary Operation: {str(op.type)}, op: {str(op)}")

        state.set_symbolic_var(op, op.lvalue, sym_rvalue)

    def parse_index(self, op: Index, state: SymbolicState):
        # 获取数组/映射中Index位置，然后对该位置的数据进行赋值
        # 1.获取被索引的符号变量（数组/映射）
        # sym_arr_or_map = state.get_or_create_default_symbolic_var(op.variable_left)
        # # 2.获取索引的符号变量
        # sym_index = state.get_or_create_default_symbolic_var(op.variable_right)
        # # 3.element
        # sym_elem = None
        # # 4. 判断是数组还是映射，进行相应的处理
        # arr_or_map_type = op.variable_left.type
        # if isinstance(arr_or_map_type, ArrayType):  # 数组
        #     elem_type = arr_or_map_type.type
        #     # 符号化数组元素
        #     sym_elem = Select(sym_arr_or_map, sym_index)
        # elif isinstance(arr_or_map_type, MappingType):  # 映射
        #     key_type = arr_or_map_type.type_from
        #     sym_elem = Select(sym_arr_or_map, sym_index)
        #
        # if sym_elem is not None:
        #     state.set_symbolic_var(op.lvalue, sym_elem)
        return

    def parse_member(self, op: Member, state: SymbolicState):
        # 暂不支持对结构体的处理
        return

    def parse_nop(self, op: Nop, state: SymbolicState):
        return

        # ================================== Utils ==================================

    @staticmethod
    def convert_to_non_ssa_var(var: Union[AllIRVarType, Variable]) -> NonSSAVarType:
        if hasattr(var, "non_ssa_version"):
            return var.non_ssa_version
        else:
            return var
