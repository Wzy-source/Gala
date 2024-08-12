from typing import Dict, List
from slither.core.variables import Variable, StateVariable
from slither.core.declarations import SolidityVariableComposed
from slither.slithir.operations import Operation
from z3 import ExprRef, Solver, Int, String, BitVec, BitVecVal, Bool, Array, BitVecSort, ArraySort
from .memory_model import MULocation, MemoryModel
from gala.sequence import Transaction
from slither.core.solidity_types import ElementaryType, ArrayType, MappingType, Type
from slither.exceptions import SlitherException


# SOLIDITY_VARIABLES = {
#     "block.basefee": "uint256",
#     "block.blobbasefee": "uint256",
#     "block.coinbase": "address",
#     "block.difficulty": "uint256",
#     "block.prevrandao": "uint256",
#     "block.gaslimit": "uint256",
#     "block.number": "uint256",
#     "block.timestamp": "uint256",
#     "block.blockhash": "bytes32",  # alias for blockhash. It's a call
#     "block.chainid": "uint256",
#     "msg.data": "bytes",
#     "msg.gas": "uint256",
#     "msg.sender": "address",
#     "msg.sig": "bytes4",
#     "msg.value": "uint256",
#     "tx.gasprice": "uint256",
#     "tx.origin": "address",
# }


class SymbolicState:
    # 符号化智能合约状态，分为Storage和Memory两种情况
    def __init__(self, tx: Transaction, init_storage: MemoryModel = None, init_tx_ctx: Dict[str, str] = None):
        # 易失性的存储
        self.memory: MemoryModel = MemoryModel(MULocation.MEMORY)
        # 设置非易失存储
        self.storage: MemoryModel = init_storage if init_storage is None else MemoryModel(MULocation.STORAGE)
        # 函数调用栈
        self.call_stack: List[Variable] = list()
        # 当前交易
        self.tx: Transaction = tx
        # 设置交易执行的上下文（msg.sender）
        self.ctx: Dict[str, ExprRef] = dict()
        self.set_init_ctx(init_tx_ctx)

    def get_or_create_default_symbolic_var(self, slither_var: Variable):
        # 先转为non_ssa版本
        var_key = self.convert_to_non_ssa_variable(slither_var)

        if isinstance(var_key, SolidityVariableComposed):  # 执行环境上下文
            return self.ctx[var_key.name]
        elif isinstance(var_key, StateVariable):  # 状态变量
            return self.storage[var_key]
        else:
            return self.memory[var_key]  # 局部变量

    def set_symbolic_var(self, slither_var: Variable, value):
        var_key = self.convert_to_non_ssa_variable(slither_var)

        if isinstance(var_key, StateVariable):
            self.storage[var_key] = value
        else:
            self.memory[var_key] = value

    def set_init_ctx(self, init_tx_ctx: Dict[str, str]) -> None:
        # 如果设定的上下文包含字段的默认信息，则设置为具体值，否则依然设置为符号值
        for key in init_tx_ctx.keys():
            assert isinstance(key, str), "Wrong type for init ctx key: {}".format(key)

        # ================ msg ================
        if "msg.sender" in init_tx_ctx:
            self.ctx["msg.sender"] = BitVecVal(int(init_tx_ctx["msg.sender"], 16), 160)
        else:
            self.ctx["msg.sender"] = BitVec("msg.sender", 160)

        if "msg.value" in init_tx_ctx:
            self.ctx["msg.value"] = BitVecVal(int(init_tx_ctx["msg.value"]), 256)
        else:
            self.ctx["msg.value"] = BitVec("msg.value", 256)

        if "msg.data" in init_tx_ctx:
            self.ctx["msg.data"] = BitVecVal(int(init_tx_ctx["msg.data"], 16), 256)
        else:
            self.ctx["msg.data"] = BitVec("msg.data", 256)

        if "msg.gas" in init_tx_ctx:
            self.ctx["msg.gas"] = BitVecVal(int(init_tx_ctx["msg.gas"]), 256)
        else:
            self.ctx["msg.gas"] = BitVec("msg.gas", 256)

        if "msg.sig" in init_tx_ctx:
            self.ctx["msg.sig"] = BitVecVal(int(init_tx_ctx["msg.sig"], 16), 32)
        else:
            self.ctx["msg.sig"] = BitVec("msg.sig", 32)

        # ================ block ================

        if "block.number" in init_tx_ctx:
            self.ctx["block.number"] = BitVecVal(int(init_tx_ctx["block.number"]), 256)
        else:
            self.ctx["block.number"] = BitVec("block.number", 256)

        if "block.timestamp" in init_tx_ctx:
            self.ctx["block.timestamp"] = BitVecVal(int(init_tx_ctx["block.timestamp"]), 256)
        else:
            self.ctx["block.timestamp"] = BitVec("block.timestamp", 256)

        if "block.difficulty" in init_tx_ctx:
            self.ctx["block.difficulty"] = BitVecVal(int(init_tx_ctx["block.difficulty"]), 256)
        else:
            self.ctx["block.difficulty"] = BitVec("block.difficulty", 256)

        # ================ tx ================

        if "tx.origin" in init_tx_ctx:
            self.ctx["tx.origin"] = BitVecVal(int(init_tx_ctx["tx.origin"], 16), 160)
        else:
            self.ctx["tx.origin"] = BitVec("tx.origin", 160)

    @staticmethod
    def convert_to_non_ssa_variable(var: Variable) -> Variable:
        if hasattr(var, "non_ssa_version"):
            return var.non_ssa_version
        else:
            return var
