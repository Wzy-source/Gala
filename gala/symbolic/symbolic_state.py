from typing import Dict, List
from slither.core.variables import Variable, StateVariable
from slither.slithir.operations import Operation
from z3 import ExprRef, Solver, Int
from .memory_model import MULocation, MemoryModel
from gala.sequence import Transaction


class SymbolicState:
    # 符号化智能合约状态，分为Storage和Memory两种情况
    def __init__(self, solver: Solver, tx: Transaction, default_storage: MemoryModel = None, default_tx_ctx: Dict = None):
        # 易失性的存储
        self.memory: MemoryModel = MemoryModel(MULocation.MEMORY)
        # 设置非易失存储
        self.storage: MemoryModel = default_storage if default_storage is None else MemoryModel(MULocation.STORAGE)
        # 函数调用栈
        self.call_stack: List[ExprRef] = list()
        # 当前交易
        self.tx: Transaction = tx
        # 设置交易执行的上下文（msg.sender）
        self.ctx: Dict = default_tx_ctx if default_tx_ctx is not None else dict()
        # solver
        self.solver: Solver = solver

    def get_symbolic_var(self, slither_var: Variable):
        if isinstance(slither_var, StateVariable):
            if slither_var in self.storage:
                return self.storage[slither_var]
            else:
                return self.create_symbolic_var(slither_var)
        else:
            if slither_var in self.memory:
                return self.memory[slither_var]
            else:
                return self.create_symbolic_var(slither_var)  # 创建一个新的变量，并添加约束

    def create_symbolic_var(self, slither_var: Variable):
        return Int('x')
