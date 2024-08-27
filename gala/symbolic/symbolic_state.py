from typing import Dict, List, Union
from slither.core.variables import Variable, StateVariable
from slither.slithir.variables import ReferenceVariable, Constant
from slither.core.declarations import SolidityVariableComposed
from slither.slithir.operations import Operation
from z3 import ExprRef, Solver, Int, String, BitVec, BitVecVal, Bool, Array, BitVecSort, ArraySort, BitVecRef, BoolRef,Or
from .memory_model import MULocation, MemoryModel
from gala.sequence import Transaction
from .variable_monitor import VariableMonitor
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
    # 符号化智能合约的执行期间的状态，分为Storage和Memory两种情况
    def __init__(self, solver: Solver, monitor: VariableMonitor, tx: Transaction, tx_storage: MemoryModel,
                 tx_ctx: Dict[str, Union[str, List]] = None):
        # 约束求解器
        self.solver = solver
        # 状态变量检测器
        self.monitor = monitor
        # 易失性的存储
        self.memory: MemoryModel = MemoryModel(MULocation.MEMORY)
        # 设置非易失存储
        self.storage: MemoryModel = tx_storage
        # 函数调用栈
        self.call_stack: List[Variable] = list()
        # 当前交易
        self.tx: Transaction = tx
        # 设置交易执行的上下文（msg.sender）
        self.ctx: Dict[str, ExprRef] = dict()
        self.set_init_ctx(tx_ctx)

    def get_or_create_default_symbolic_var(self, slither_var: Variable):
        # 先转为non_ssa版本
        var_key = self.convert_to_non_ssa_variable(slither_var)

        if isinstance(var_key, SolidityVariableComposed):  # 执行环境上下文
            return self.ctx[var_key.name]

        elif self.is_or_point_to_state_variable(var_key):  # 状态变量
            if var_key in self.storage:
                return self.storage[var_key]
            else:
                sym_res = self.storage.create_var(var_key)
                # 为新创建的状态变量默认值符号值添加约束
                self.add_constraint_for_created_state_var(sym_res)
                return sym_res
        else:
            if var_key in self.memory:
                return self.memory[var_key]
            else:
                return self.memory.create_var(var_key)  # 局部变量，不设定初始值

    def add_constraint_for_created_state_var(self, sym_var: ExprRef):
        if isinstance(sym_var, BitVecRef):
            self.solver.add(sym_var == 0)
        elif isinstance(sym_var, BoolRef):
            self.solver.add(sym_var == False)

    def set_symbolic_var(self, op: Operation, slither_var: Variable, sym_value: ExprRef):
        var_key = self.convert_to_non_ssa_variable(slither_var)

        if self.is_or_point_to_state_variable(var_key):
            self.monitor.notify_in_change(op, var_key, sym_value, self.tx, self.ctx)
            self.storage[var_key] = sym_value
        else:
            self.memory[var_key] = sym_value

    def set_init_ctx(self, init_tx_ctx: Dict[str, Union[str, List]]) -> None:
        init_tx_ctx = {} if init_tx_ctx is None else init_tx_ctx
        # 如果设定的上下文包含字段的默认信息，则设置为具体值，否则依然设置为符号值
        for key in init_tx_ctx.keys():
            assert isinstance(key, str), "Wrong type for init ctx key: {}".format(key)

        # ================ msg ================
        if "msg.sender" in init_tx_ctx:
            sender = init_tx_ctx["msg.sender"]
            if isinstance(sender, str):
                self.ctx["msg.sender"] = BitVecVal(int(sender, 16), 256)
            elif isinstance(sender, List):
                # 创建一个包含约束的符号化变量
                sym_sender = BitVec(f"msg.sender({self.tx.function.name})", 256)
                constraint_list = []
                for addr in sender:
                    constraint_list.append(sym_sender == BitVecVal(int(addr, 16), 256))
                self.solver.add(Or(constraint_list))
                self.ctx["msg.sender"] = sym_sender
        else:
            self.ctx["msg.sender"] = BitVec("msg.sender", 256)

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

        if "block.chainid" in init_tx_ctx:
            self.ctx["block.chainid"] = BitVecVal(int(init_tx_ctx["block.chainid"]), 256)
        else:
            self.ctx["block.chainid"] = BitVec("block.chainid", 256)

        # ================ tx ================

        if "tx.origin" in init_tx_ctx:
            origin = init_tx_ctx["tx.origin"]
            if isinstance(origin, str):
                self.ctx["tx.origin"] = BitVecVal(int(origin, 16), 256)
            elif isinstance(origin, List):
                sym_origin = BitVec("tx.origin", 256)
                constraint_list = []
                for addr in origin:
                    constraint_list.append(sym_origin == BitVecVal(int(addr, 16), 256))
                self.solver.add(Or(constraint_list))
                self.ctx["tx.origin"] = sym_origin
        else:
            self.ctx["tx.origin"] = BitVec("tx.origin", 256)

    @staticmethod
    def convert_to_non_ssa_variable(var: Variable) -> Variable:
        if hasattr(var, "non_ssa_version"):
            return var.non_ssa_version
        else:
            return var

    @staticmethod
    def is_or_point_to_state_variable(var: Variable) -> bool:
        if isinstance(var, StateVariable):
            return True
        elif isinstance(var, ReferenceVariable):
            if isinstance(var.points_to_origin, StateVariable):
                return True
        else:
            return False
