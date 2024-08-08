from z3 import Solver, sat, unsat, Z3Exception, unknown, Bool, Int, String, ExprRef, Or, Not, BitVecRef, And
from slither.slithir.operations import *
from slither.slithir.variables import *
from slither.core.variables import Variable
from typing import List, Dict, Union, TypeAlias
from .variable_extractor import Z3VariableExtractor
from .var_types import AllIRVarType, NonSSAVarType, ConstantWrapper
from gala.graph import EdgeType, SlicedPath
from gala.sequence import Transaction

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


class OperationProcessor:
    def __init__(self, z3_solver: Solver):
        self.z3_solver: Solver = z3_solver
        self.z3_variable_extractor: Z3VariableExtractor = Z3VariableExtractor()
        self.operation_processors: Dict = self.register_op_processors()

    def register_op_processors(self) -> Dict:
        return {
            Assignment: self.process_assignment,
            TypeConversion: self.process_type_conversion,
            SolidityCall: self.process_solidity_call,
            Binary: self.process_binary,
            Condition: self.process_condition,
            Return: self.process_return,
            Phi: self.process_phi,
            Unary: self.process_unary,
            Index: self.process_index,
            Member: self.process_member,
            FunctionCall: self.process_function_call,
            Length: self.process_length
        }

    def process_tx_ops(self, tx: Transaction):
        # 处理Slither指令的调用序列
        self.z3_solver.reset()
        slither_z3_var_map: Dict[NonSSAVarType, ExprRef] = dict()
        call_stack: List[ExprRef] = list()

        operations: List[Operation] = list(filter(lambda n: isinstance(n, Operation), tx.exec_path.path))
        exec_path: SlicedPath = tx.exec_path
        for op in operations:
            self.process_one_op(op, exec_path, slither_z3_var_map, call_stack)

    def process_one_op(self, op: Operation, exec_path: SlicedPath, var_map: Dict[NonSSAVarType, ExprRef], call_stack: List[ExprRef]) -> None:

        for op_type in self.operation_processors.keys():
            if isinstance(op, op_type):
                self.operation_processors[op_type](op, exec_path, var_map, call_stack)
                return

    # ================================== Processors ==================================

    def process_assignment(self, op: Assignment, exec_path: SlicedPath, var_table: Dict[NonSSAVarType, ExprRef], call_stack: List[ExprRef]):
        z3_lvar = self.get_z3_variable(op.lvalue, var_table)
        z3_rvar = self.get_z3_variable(op.rvalue, var_table)
        self.z3_solver.add(z3_lvar == z3_rvar)

    def process_length(self, op: Assignment, exec_path: SlicedPath, var_table: Dict[NonSSAVarType, ExprRef], call_stack: List[ExprRef]):
        # Trade-off：对于Length操作，并不精确的表示数组的长度，而是粗略地生成一个长度大于等于0的整数值即可
        z3_lvar = self.get_z3_variable(op.lvalue, var_table)
        self.z3_solver.add(z3_lvar >= 0)

    def process_function_call(self, op: FunctionCall, exec_path: SlicedPath, var_table: Dict[NonSSAVarType, ExprRef], call_stack: List[ExprRef]):
        if op.lvalue is not None and op in exec_path.call_nodes:
            z3_lvar = self.get_z3_variable(op.lvalue, var_table)
            # 使用栈来记录return destination
            call_stack.append(z3_lvar)

    def process_type_conversion(self, op: TypeConversion, exec_path: SlicedPath, var_table: Dict[NonSSAVarType, ExprRef], call_stack: List[ExprRef]):
        # 根据转换的类型，直接创建一个新的变量
        z3_lvar = self.get_z3_variable(op.lvalue, var_table)
        z3_src_var = self.get_z3_variable(op.variable, var_table)  # TODO debug
        if type(z3_lvar) == type(z3_src_var):
            self.z3_solver.add(z3_lvar == z3_src_var)

    def process_solidity_call(self, op: SolidityCall, exec_path: SlicedPath, var_table: Dict[NonSSAVarType, ExprRef], call_stack: List[ExprRef]):
        if "require" in str(op) or "assert" in str(op):
            arg = op.arguments[0]
            z3_var = self.get_z3_variable(arg, var_table)
            self.z3_solver.add(z3_var == True)

    def process_binary(self, op: Binary, exec_path: SlicedPath, var_table: Dict[NonSSAVarType, ExprRef], call_stack: List[ExprRef]) -> None:
        operator: BinaryType = op.type
        z3_lvar = self.get_z3_variable(op.lvalue, var_table)
        z3_rvar0 = self.get_z3_variable(op.variable_left, var_table)
        z3_rvar1 = self.get_z3_variable(op.variable_right, var_table)
        # According to the operator, processing the three values.
        match operator:
            case BinaryType.EQUAL:
                self.z3_solver.add(z3_lvar == (z3_rvar0 == z3_rvar1))
            case BinaryType.NOT_EQUAL:
                self.z3_solver.add(z3_lvar == (z3_rvar0 != z3_rvar1))
            case BinaryType.GREATER:
                self.z3_solver.add(z3_lvar == (z3_rvar0 > z3_rvar1))
            case BinaryType.GREATER_EQUAL:
                self.z3_solver.add(z3_lvar == (z3_rvar0 >= z3_rvar1))
            case BinaryType.LESS:
                self.z3_solver.add(z3_lvar == (z3_rvar0 < z3_rvar1))
            case BinaryType.LESS_EQUAL:
                self.z3_solver.add(z3_lvar == (z3_rvar0 <= z3_rvar1))
            case BinaryType.ADDITION:
                self.z3_solver.add(z3_lvar == (z3_rvar0 + z3_rvar1))
            case BinaryType.MULTIPLICATION:
                self.z3_solver.add(z3_lvar == (z3_rvar0 * z3_rvar1))
            case BinaryType.SUBTRACTION:
                self.z3_solver.add(z3_lvar == (z3_rvar0 - z3_rvar1))
            case BinaryType.DIVISION:
                self.z3_solver.add(z3_lvar == (z3_rvar0 / z3_rvar1))
            case BinaryType.MODULO:
                self.z3_solver.add(z3_lvar == (z3_rvar0 % z3_rvar1))
            case BinaryType.POWER:
                self.z3_solver.add(z3_lvar == (z3_rvar0 ** z3_rvar1))
            case BinaryType.OR:
                self.z3_solver.add(z3_lvar == (z3_rvar0 | z3_rvar1))
            case BinaryType.AND:
                self.z3_solver.add(z3_lvar == (z3_rvar0 & z3_rvar1))
            case BinaryType.CARET:
                self.z3_solver.add(z3_lvar == (z3_rvar0 ^ z3_rvar1))
            case BinaryType.RIGHT_SHIFT:
                self.z3_solver.add(z3_lvar == (z3_rvar0 >> z3_rvar1))
            case BinaryType.LEFT_SHIFT:
                self.z3_solver.add(z3_lvar == (z3_rvar0 << z3_rvar1))
            case BinaryType.OROR:
                self.z3_solver.add(z3_lvar == Or(z3_rvar0, z3_rvar1))
            case BinaryType.ANDAND:
                self.z3_solver.add(z3_lvar == And(z3_rvar0, z3_rvar1))
            case _:
                raise Exception(f"Unknown Binary Operation: {operator}")

    def process_condition(self, op: Condition, exec_path: SlicedPath, var_table: Dict[NonSSAVarType, ExprRef], call_stack: List[ExprRef]):
        edge_type: EdgeType = exec_path.condition_node_edge_type_map[op]
        z3var = self.get_z3_variable(op.read[0], var_table)
        if edge_type == EdgeType.IF_TRUE:
            self.z3_solver.add(z3var == True)
        elif edge_type == EdgeType.IF_FALSE:
            self.z3_solver.add(z3var == False)
        else:
            raise Exception(f"Unknown Condition Result: {str(edge_type)}, op: {str(op)}")

    def process_return(self, op: Return, exec_path: SlicedPath, var_table: Dict[NonSSAVarType, ExprRef], call_stack: List[ExprRef]):
        returned_value = op.used[0]
        z3_return_var = self.get_z3_variable(returned_value, var_table)
        # get the returning destination from the call stack
        if call_stack:
            z3_dst_var = call_stack.pop()
            # let the return_dst be equal to the current returned value.
            if type(z3_dst_var) == type(z3_return_var):
                self.z3_solver.add(z3_dst_var == z3_return_var)

    def process_phi(self, op: Phi, exec_path: SlicedPath, var_table: Dict[NonSSAVarType, ExprRef], call_stack: List[ExprRef]):
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
            z3_lvar = self.get_z3_variable(lvalue, var_table)

            for rvalue in rvalue_list:
                z3_rvar = self.get_z3_variable(rvalue, var_table)
                constraints_list.append(z3_rvar == z3_lvar)
            # OR relations
            self.z3_solver.add(Or(constraints_list))

    def process_unary(self, op: Unary, exec_path: SlicedPath, var_table: Dict[NonSSAVarType, ExprRef], call_stack: List[ExprRef]):
        # 一元操作
        z3_lvar = self.get_z3_variable(op.lvalue, var_table)
        z3_rvar = self.get_z3_variable(op.rvalue, var_table)
        if op.type == UnaryType.BANG:  # 非操作
            self.z3_solver.add(z3_lvar == Not(z3_rvar))
        elif op.type == UnaryType.TILD:
            # Bitwise NOT
            if isinstance(z3_rvar, BitVecRef):
                # Ensure the operand is treated as a bit-vector for bitwise operations
                self.z3_solver.add(z3_lvar == ~z3_rvar)
            else:
                raise TypeError("Operand for bitwise NOT must be a BitVecRef")

        else:
            raise Exception(f"Unknown Unary Operation: {str(op.type)}, op: {str(op)}")

    def process_index(self, op: Index, exec_path: SlicedPath, var_table: Dict[NonSSAVarType, ExprRef], call_stack: List[ExprRef]):
        return

    def process_member(self, op: Member, exec_path: SlicedPath, var_table: Dict[NonSSAVarType, ExprRef], call_stack: List[ExprRef]):
        return

    # ================================== Utils ==================================

    def get_z3_variable(self, slither_var: Union[AllIRVarType, Variable], slither_z3_var_map: Dict[NonSSAVarType, ExprRef]) -> Union[
        Bool, String, Int]:
        # 转换为non ssa的形式，作为字典的key
        slither_var: NonSSAVarType = self.convert_to_non_ssa_var(slither_var)

        if slither_var in slither_z3_var_map.keys():
            return slither_z3_var_map[slither_var]
        else:
            # 如果是常量，由于在Slither的实现中，常量的哈希的计算方式是：self._val.__hash__()
            # 我们需要对每一个常量进行区分，所以设计了ConstantWrapper
            if isinstance(slither_var, Constant):
                constant_wrapper, new_z3_var = self.z3_variable_extractor.extract_z3_constant(slither_var)
                self.z3_solver.add(new_z3_var == constant_wrapper.origin.value)
                slither_z3_var_map[constant_wrapper] = new_z3_var
            else:
                new_z3_var = self.z3_variable_extractor.extract_z3_var(slither_var)
                slither_z3_var_map[slither_var] = new_z3_var

            return new_z3_var

    @staticmethod
    def convert_to_non_ssa_var(var: Union[AllIRVarType, Variable]) -> NonSSAVarType:
        if hasattr(var, "non_ssa_version"):
            return var.non_ssa_version
        else:
            return var
