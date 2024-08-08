from typing import TypeAlias, Union, Dict, Tuple
from z3 import Solver, String, Int, Bool, Or, Not, BoolRef, ArithRef, And, Z3Exception, ExprRef
from slither.slithir.variables import *
from slither.slithir.operations import *
from slither.core.solidity_types import UserDefinedType
from slither.core.variables.state_variable import StateVariable
from slither.core.variables.local_variable import LocalVariable
from slither.core.declarations.solidity_variables import SolidityVariableComposed, SolidityVariable
from .var_types import AllIRVarType, NonSSAVarType, ConstantWrapper

solidity_z3_var_map: Dict[str, ExprRef] = {
    "msg.sender": String("msg.sender"),
    "msg.value": String("msg.value"),
    "block.number": Int("block.number"),
    "block.timestamp": Int("block.timestamp"),
    "tx.origin": String("tx.origin"),
}


class Z3VariableExtractor:
    def __init__(self):
        pass

    @staticmethod
    def extract_z3_var(slither_var: NonSSAVarType) -> Union[Bool, String, Int]:
        # 处理solidity variable
        if isinstance(slither_var, SolidityVariableComposed):
            if slither_var.name in solidity_z3_var_map.keys():
                return solidity_z3_var_map[slither_var.name]
        # 处理constant
        elif isinstance(slither_var, ConstantWrapper):
            var_value: Union[str, int, bool] = slither_var.origin.value
            var_name: str = str(slither_var)
            if isinstance(var_value, int):
                return Int(var_name)
            elif isinstance(var_value, bool):
                return Bool(var_name)
            elif isinstance(var_value, str):
                return String(var_name)
        else:
            # 基于变量在Slither中的类型来创建Z3变量
            # TODO 优化类型
            var_type = str(slither_var.type)
            if isinstance(slither_var, Union[TemporaryVariable, SolidityVariable, ReferenceVariable, TupleVariable]):
                var_name = slither_var.name
            else:
                var_name = slither_var.canonical_name
                # Apply the String variable to represent the address variables.
            if var_type == "address":
                addr_var = String(var_name)
                return addr_var

            elif var_type == "bool":
                bool_var = Bool(var_name)
                return bool_var

                # Roughly regard all the uint and int variables are Int
            elif "int" in var_type:
                int_var = Int(var_name)
                return int_var

            elif "string" in var_type or "bytes" in var_type:
                byte_var = String(var_name)
                return byte_var
            else:
                return String(var_name)

    @staticmethod
    def extract_z3_constant(constant_var: Constant) -> Tuple[ConstantWrapper, Union[Bool, String, Int]]:
        constant_wrapper = ConstantWrapper(constant_var)
        var_value: Union[str, int, bool] = constant_wrapper.origin.value
        var_name: str = str(constant_wrapper)
        if isinstance(var_value, int):
            return constant_wrapper, Int(var_name)
        elif isinstance(var_value, bool):
            return constant_wrapper, Bool(var_name)
        elif isinstance(var_value, str):
            return constant_wrapper, String(var_name)
        else:
            raise Exception(f"Unknown Constant value: {str(constant_var)}")
