from z3 import Solver, sat, unsat, Z3Exception, unknown, ExprRef, BitVecVal
from .slither_op_parser import SlitherOpParser
from gala.sequence import TxSeqGenerationResult, TxSequence
from typing import Set, List, Dict
from gala.graph import ICFGNode, SlicedGraph
from .symbolic_state import SymbolicState
from slither.core.variables import StateVariable
from slither.core.declarations import Function
from .memory_model import MemoryModel, MULocation
from .default_ctx import DEFAULT_TX_CTX, DEFAULT_CONSTRUCTOR_CTX
from gala.graph.permission import Permission, PermissionTaintResult


class SymbolicEngine:
    def __init__(self):
        self.solver: Solver = Solver()
        self.slither_op_parser: SlitherOpParser = SlitherOpParser(self.solver)

    def execute(self, sliced_graph: SlicedGraph, all_tx_sequences: TxSeqGenerationResult) -> None:
        # 返回执行结果，提供给Logger使用
        for base_path_tx_seqs_map in all_tx_sequences.values():
            for base_path in base_path_tx_seqs_map.keys():
                tx_seq_set: Set[TxSequence] = base_path_tx_seqs_map[base_path][0]
                perm_nodes: List[ICFGNode] = base_path_tx_seqs_map[base_path][1]
                for one_seq in tx_seq_set:
                    # 每次执行完毕一次交易序列，重置约束求解器，清空约束
                    self.solver.reset()
                    # 持久化存储，持久存在于交易之间
                    init_storage: MemoryModel = MemoryModel(MULocation.STORAGE)
                    # 设置构造函数的上下文
                    self.init_constructor(init_storage, sliced_graph)
                    is_tx_secure: bool = self.exec_one_tx_sequence(init_storage, one_seq)

                    if is_tx_secure:
                        print("Current Txs:", one_seq, "No Solution Found, the Sequence is Secure.")
                    else:  # 输出潜在的交易序列是不安全的情况
                        print("Current Txs May Be Insecure! Txs:", one_seq, "Solver Assertions:", self.solver.assertions())

    def exec_one_tx_sequence(self, init_storage: MemoryModel, tx_sequence: TxSequence) -> bool:
        # 设置默认的交易执行上下文
        default_context = DEFAULT_TX_CTX
        for tx in tx_sequence.txs:
            # 设置下一次执行的的初始状态 符号执行每一个交易，保存交易的中间状态
            entry_state: SymbolicState = SymbolicState(tx=tx, init_storage=init_storage, init_tx_ctx=default_context)
            self.slither_op_parser.parse_tx_ops(entry_state)
            # 检查结果是否是“不可满足的”，说明合约是安全的
            if self.solver.check() == unsat:
                return True
        # 打印一个可行解中的每一个元素
        print("One Possible Value For Each State Variable:")
        model = self.solver.model()
        for var in model:
            print(f"{var} = {model[var]}")

    @staticmethod
    def init_constructor(init_storage: MemoryModel, sliced_graph: SlicedGraph) -> None:
        constructor: Function = sliced_graph.icfg.main_contract.constructor
        constr_slice = sliced_graph.func_slices_map[constructor][0]
        for sv_write_node in constr_slice.sv_write_nodes:
            if hasattr(sv_write_node, "lvalue") and str(sv_write_node.lvalue.type) == "address":
                perm: Permission = sliced_graph.icfg.graph.nodes[sv_write_node]["permission"]
                solidity_vars_flow = perm.state_var_write_taint_result[constr_slice].solidity_vars_flow_to_sink
                for svf in solidity_vars_flow:
                    if svf.name in DEFAULT_CONSTRUCTOR_CTX.keys():
                        default_addr = DEFAULT_CONSTRUCTOR_CTX[svf.name]
                        init_storage[sv_write_node.lvalue] = BitVecVal(int(default_addr, 16), 160)
