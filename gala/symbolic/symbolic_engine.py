from z3 import Solver, sat, unsat, Z3Exception, unknown
from .operation_processor import OperationProcessor
from gala.sequence import TxSeqGenerationResult, TxSequence
from typing import Set, List
from gala.graph import ICFGNode, SlicedGraph


class SymbolicEngine:
    def __init__(self):
        self.z3_solver: Solver = Solver()
        self.operation_processor: OperationProcessor = OperationProcessor(self.z3_solver)

    def execute(self, all_tx_sequences: TxSeqGenerationResult) -> None:
        for sequences_and_perms in all_tx_sequences.values():
            tx_seq_set: Set[TxSequence] = sequences_and_perms[0]
            perm_list: List[ICFGNode] = sequences_and_perms[1]
            for one_seq in tx_seq_set:
                self.check_one_tx_sequence(one_seq)

    def check_one_tx_sequence(self, tx_sequence: TxSequence) -> str:
        # TODO 连续发起多个交易，每一个交易均具有不同的上下文
        # 保存一个交易的中间状态
        for tx in tx_sequence.transactions:
            # 符号执行每一个交易，保存交易的中间状态
            self.operation_processor.process_tx_ops(tx)
        return "secure"
