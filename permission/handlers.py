from slither.core.declarations import Contract
from slither.core.variables import Variable
from slither.slithir.operations import Operation
from gala.sequence.transaction import Transaction
from z3 import ExprRef
from typing import Dict, Callable


class Handlers:
    def __init__(self):
        self.owner_list = []

    def handle_owner_change(self, op: Operation, var: Variable, sym_val: ExprRef, tx: Transaction, ctx: Dict[str, ExprRef]):
        owner_address = sym_val.as_long()
        attacker_address = int("0xcfd06749b04cc6ec83a60ff8df7e7936385d05b0", 16)
        if owner_address == attacker_address:
            print("owner change")

    def get(self) -> Dict[str, Callable]:
        return {
            "owner": self.handle_owner_change
        }
