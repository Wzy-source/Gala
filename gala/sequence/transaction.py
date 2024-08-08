from gala.graph import ICFG, ICFGNode, Permission, SlicedPath
from typing import List, Optional
from slither.core.declarations import Function

DEFAULT_MAX_TX_NUM: int = 5


class Transaction:
    # 交易信息，包含了交易的上下文和函数执行切片
    def __init__(self, exec_path: SlicedPath):
        self.exec_path: SlicedPath = exec_path
        self.function: Function = exec_path.slice_func
        self.context: Optional = None

    def __str__(self):
        return str(self.function)


class TxSequence:
    def __init__(self, base_tx: Transaction, max_tx_num: int = DEFAULT_MAX_TX_NUM):
        self.base_tx: Transaction = base_tx
        self.max_tx_num: int = max_tx_num
        self.reversed_txs: List[Transaction] = [base_tx]

    @property
    def transactions(self) -> List[Transaction]:
        return list(reversed(self.reversed_txs))

    def add_tx_happens_before(self, tx: Transaction) -> bool:
        # 不超过最大交易数量
        if len(self.reversed_txs) == self.max_tx_num:
            return False
        self.reversed_txs.append(tx)
        return True

    def copy(self) -> 'TxSequence':
        # 这里使用了浅拷贝
        copied_reversed_txs = []
        # 浅拷贝每一个对象
        for tx in self.reversed_txs:
            copied_reversed_txs.append(tx)
        # 创建一个新的 TxSequence 对象
        new_tx_sequence = TxSequence(self.base_tx, self.max_tx_num)
        new_tx_sequence.reversed_txs = copied_reversed_txs

        return new_tx_sequence

    def __str__(self):
        return " -> ".join(str(tx) for tx in self.transactions)
