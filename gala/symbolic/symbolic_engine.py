from z3 import Solver, sat, unsat, Z3Exception, unknown, ExprRef
from .slither_op_parser import SlitherOpParser
from gala.sequence import TxSeqGenerationResult, TxSequence
from typing import Set, List, Dict
from gala.graph import ICFGNode, SlicedGraph
from .symbolic_state import SymbolicState
from slither.core.variables import StateVariable
from .memory_model import MemoryModel, MULocation


class SymbolicEngine:
    def __init__(self):
        self.solver: Solver = Solver()
        self.slither_op_parser: SlitherOpParser = SlitherOpParser(self.solver)

    def execute(self, all_tx_sequences: TxSeqGenerationResult) -> None:
        for sequences_and_perms in all_tx_sequences.values():
            tx_seq_set: Set[TxSequence] = sequences_and_perms[0]
            perm_list: List[ICFGNode] = sequences_and_perms[1]
            for one_seq in tx_seq_set:
                self.exec_one_tx_sequence(one_seq)

    def exec_one_tx_sequence(self, tx_sequence: TxSequence) -> str:

        # TODO default_context
        # 保存一个交易的中间状态
        default_storage: MemoryModel = MemoryModel(MULocation.STORAGE)
        for tx in tx_sequence.transactions:
            self.solver.reset()
            entry_state: SymbolicState = SymbolicState(solver=self.solver, tx=tx, default_storage=default_storage)
            # 符号执行每一个交易，保存交易的中间状态
            self.slither_op_parser.parse_tx_ops(entry_state)  # TODO 返回执行结果
        return "secure"
