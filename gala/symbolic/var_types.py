from typing import TypeAlias, Union, Dict
from slither.slithir.variables import *
from slither.core.variables.state_variable import StateVariable
from slither.core.variables.local_variable import LocalVariable
from slither.core.declarations.solidity_variables import SolidityVariableComposed, SolidityVariable


class ConstantWrapper:
    def __init__(self, var: Constant) -> None:
        self.origin: Constant = var

    def __str__(self) -> str:
        str_constant = str(self.origin)
        type_constant = type(self.origin.value)
        return f"{str_constant}: {type_constant}"

    def __repr__(self) -> str:
        return self.__str__()

    def __hash__(self) -> int:
        return hash(self.__str__())


AllIRVarType: TypeAlias = Union[
    Constant,
    ReferenceVariable,
    TemporaryVariable,
    TemporaryVariableSSA,
    TupleVariable,
    TupleVariableSSA,
    LocalIRVariable,
    StateIRVariable,
    SolidityVariableComposed,
]

NonSSAVarType: TypeAlias = Union[
    Constant,
    ConstantWrapper,
    StateVariable,
    LocalVariable,
    TupleVariable,
    TemporaryVariable,
    ReferenceVariable,
    SolidityVariableComposed,
]
