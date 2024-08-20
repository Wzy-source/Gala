from typing import List, Dict, Callable
from slither.core.variables import StateVariable, Variable
from slither.slithir.operations import Operation
from z3 import ExprRef
from gala.sequence.transaction import Transaction


class VariableMonitor:
    def __init__(self):
        self.var_handlers: Dict[Variable, Callable] = dict()

    def add_var_handler(self, var: Variable, handler: Callable):
        self.var_handlers[var] = handler

    def notify_in_change(self, op: Operation, variable: Variable, sym_value: ExprRef, tx: Transaction, ctx: Dict[str, ExprRef]):
        # 每一次状态变更，都会调用预先设定好的函数
        if variable in self.var_handlers.keys():
            self.var_handlers[variable](op, variable, sym_value, tx, ctx)
