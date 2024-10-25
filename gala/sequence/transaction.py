from gala.graph import ICFG, ICFGNode, SlicedPath
from typing import List, Optional
from slither.core.declarations import Function

DEFAULT_MAX_TX_NUM: int = 1


class Transaction:
    # 交易信息，包含了交易的上下文和函数执行切片
    def __init__(self, exec_path: SlicedPath):
        self.exec_path: SlicedPath = exec_path
        self.function: Function = exec_path.slice_func

    def __str__(self):
        return str(self.function)


class TxSequence:
    def __init__(self, txs: List[Transaction] = None, max_tx_num: int = DEFAULT_MAX_TX_NUM):
        self.max_tx_num: int = max_tx_num
        self.txs: List[Transaction] = txs if txs is not None else []

    def add_happens_before_tx(self, tx: Transaction) -> bool:
        # 不超过最大交易数量
        if len(self.txs) == self.max_tx_num:
            return False
        self.txs.insert(0, tx)
        return True

    def add_happens_after_tx(self, tx: Transaction) -> bool:
        if len(self.txs) == self.max_tx_num:
            return False
        self.txs.append(tx)
        return True

    def copy(self) -> 'TxSequence':
        # 这里使用了浅拷贝
        copied_txs = []
        # 浅拷贝每一个对象
        for tx in self.txs:
            copied_txs.append(tx)
        # 创建一个新的 TxSequence 对象
        return TxSequence(copied_txs, self.max_tx_num)

    def __str__(self):
        return " -> ".join(map(str, self.txs))
