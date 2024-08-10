from enum import Enum, auto

from slither.core.variables import Variable, StateVariable
from slither.slithir.operations import Operation
from z3 import ExprRef
from typing import Dict


class MULocation(Enum):
    STORAGE = auto()
    MEMORY = auto()


class MemoryModel:
    def __init__(self, mu_location: MULocation):
        self.MU: Dict[Variable, ExprRef] = dict()
        self.location: MULocation = mu_location

    def __setitem__(self, key: Variable, value: ExprRef):
        self.MU[key] = value

    def __getitem__(self, key: Variable):
        return self.MU[key]

    def __contains__(self, item: Variable) -> bool:
        return item in self.MU
