from slither.core.expressions import Literal
from slither.core.solidity_types import ElementaryType
from slither.slithir.variables import Constant
from z3 import Solver, sat, unsat, Z3Exception, unknown, ExprRef, BitVecVal, ModelRef, BitVecRef, BitVecNumRef
from .slither_op_parser import SlitherOpParser
from gala.sequence import TxSeqGenerationResult, TxSequence, Transaction
from typing import Set, List, Dict
from gala.graph import ICFGNode, SlicedGraph
from .symbolic_state import SymbolicState
from slither.core.variables import StateVariable
from slither.core.declarations import Function
from .memory_model import MemoryModel, MULocation
from .default_ctx import DEFAULT_TX_CTX, DEFAULT_CONSTRUCTOR_CTX
from gala.graph.permission import Permission, PermissionTaintResult

# ANSI 转义码
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
RESET = "\033[0m"


class SymbolicEngine:
    def __init__(self):
        self.solver: Solver = Solver()
        self.slither_op_parser: SlitherOpParser = SlitherOpParser(self.solver)

    def execute(self, sliced_graph: SlicedGraph, all_tx_sequences: TxSeqGenerationResult) -> None:
        # 返回执行结果，提供给Logger使用
        check_count = 0
        for base_path_tx_seqs_map in all_tx_sequences.values():
            for base_path in base_path_tx_seqs_map.keys():
                tx_seq_set: Set[TxSequence] = base_path_tx_seqs_map[base_path][0]
                perm_nodes: List[ICFGNode] = base_path_tx_seqs_map[base_path][1]
                for one_seq in tx_seq_set:
                    # 每次执行完毕一次交易序列，重置约束求解器，清空约束
                    self.solver.reset()
                    # 持久化存储，持久存在于交易之间
                    init_storage: MemoryModel = MemoryModel(MULocation.STORAGE)
                    # 设置合约创建时候的默认值
                    self.init_contract_creation_sym_storage(sliced_graph, init_storage)
                    # 执行一组交易序列,找到一组可行解
                    is_secure = self.exec_one_tx_sequence_with_constructor(sliced_graph, init_storage, one_seq)
                    # 输出执行结果
                    contract_name = sliced_graph.icfg.main_contract.name
                    self.log_symbolic_execution_res(is_secure, one_seq, perm_nodes, init_storage, contract_name, check_count)
                    check_count += 1

    def exec_one_tx_sequence_with_constructor(self, sliced_graph: SlicedGraph, init_storage: MemoryModel, tx_sequence: TxSequence):
        # 在每一个交易序列执行之前，先执行一遍constructor函数
        main_contract = sliced_graph.icfg.main_contract
        constructor: Function = main_contract.constructor
        if constructor is not None and constructor in main_contract.functions:
            constr_slice = sliced_graph.func_slices_map[constructor][0]
            constr_tx = Transaction(constr_slice)
            constr_init_state: SymbolicState = SymbolicState(solver=self.solver, tx=constr_tx, init_storage=init_storage,
                                                             init_tx_ctx=DEFAULT_CONSTRUCTOR_CTX)
            self.slither_op_parser.parse_tx_ops(constr_init_state)

        # 设置默认的交易执行上下文
        for tx in tx_sequence.txs:
            # 设置下一次执行的的初始状态 符号执行每一个交易，保存交易的中间状态
            tx_init_state: SymbolicState = SymbolicState(solver=self.solver, tx=tx, init_storage=init_storage,
                                                         init_tx_ctx=DEFAULT_TX_CTX)
            self.slither_op_parser.parse_tx_ops(tx_init_state)
            # 检查结果是否是“不可满足的”，说明合约是安全的
            if self.solver.check() == unsat:
                return True
        return False

    @staticmethod
    def init_contract_creation_sym_storage(sliced_graph: SlicedGraph, init_storage: MemoryModel):
        main_contract = sliced_graph.icfg.main_contract
        inited_state_vars: List[StateVariable] = list(filter(lambda sv: sv.initialized, main_contract.state_variables))
        for isv in inited_state_vars:
            # 获取初始值
            isv_exp = isv.expression
            if isv_exp is not None and isinstance(isv_exp, Literal):
                isv_type = isv_exp.type
                isv_value = isv_exp.value
                if isinstance(isv_type, ElementaryType):
                    sym_isv_constant = init_storage.create_symbolic_constant(Constant(val=isv_value, constant_type=isv_type))
                    init_storage[isv] = sym_isv_constant

    def log_symbolic_execution_res(self, is_secure: bool, txs: TxSequence, perm_nodes: List[ICFGNode], storage: MemoryModel,
                                   contract_name: str, check_count: int) -> None:
        print(f"{YELLOW}================================ GALA CHECK RESULT {check_count} FOR {contract_name} ================================{RESET}")
        # 输出攻击者和部署者的地址
        deployer_addr = DEFAULT_CONSTRUCTOR_CTX["msg.sender"]
        attacker_addr = DEFAULT_TX_CTX["msg.sender"]
        print(f"Default Deployer: {deployer_addr} ({int(deployer_addr, 16)})")
        print(f"Default Attacker: {attacker_addr} ({int(attacker_addr, 16)})")
        # 输出所有的权限集
        print(f"{CYAN}====> Permission Nodes <===={RESET}")
        for pn in perm_nodes:
            print(str(pn))
        # 输出权限集对应的交易序列
        print(f"{CYAN}====> Generated Tx Sequence <===={RESET}")
        print(f"constructor -> {str(txs)}")
        # 输出符号执行结果
        print(f"{CYAN}====> Symbolic Execution Result <===={RESET}")
        if is_secure:
            print(f"{GREEN}No Solution Found, the Sequence is Secure.{RESET}")
        else:
            print(f"{RED}Current Txs May Be Insecure!{RESET}")
            print(f"{CYAN}====> Solver Assertions <===={RESET}")
            print(self.solver.assertions())
            print(f"{CYAN}====> One Solution <===={RESET}")
            model = self.solver.model()
            for var in model:
                var_value = model[var]
                if isinstance(var_value, BitVecNumRef) and var.name().startswith("addr_"):  # 地址类型
                    var_value_hex = hex(var_value.as_long())
                    print(f"{var.name().removeprefix('addr_')} = {var_value_hex}")
                else:
                    print(f"{var.name()} = {var_value}")

        # 存储的信息
        print(f"{CYAN}====> Final Storage Value <===={RESET}")
        for state_var in storage.MU.keys():
            sym_state_val = storage[state_var]
            if isinstance(sym_state_val, BitVecNumRef) and state_var.type == "address":  # 地址类型
                var_value_hex = hex(sym_state_val.as_long())
                print(f"{state_var.name} = {var_value_hex}")
            else:
                print(f"{state_var.name} = {sym_state_val}")

    # def init_constructor(init_storage: MemoryModel, sliced_graph: SlicedGraph) -> None:
    #     if sliced_graph.icfg.main_contract.constructor is None:
    #         return
    #     constructor: Function = sliced_graph.icfg.main_contract.constructor
    #     constr_slice = sliced_graph.func_slices_map[constructor][0]
    #     for sv_write_node in constr_slice.sv_write_nodes:
    #         # 如果是address类型的变量，我们要判断msg.sender/tx.origin是否可能流向状态变量
    #         if hasattr(sv_write_node, "lvalue") and str(sv_write_node.lvalue.type) == "address":
    #             perm: Permission = sliced_graph.icfg.graph.nodes[sv_write_node]["permission"]
    #             solidity_vars_flow = perm.state_var_write_taint_result[constr_slice].solidity_vars_flow_to_sink
    #             for svf in solidity_vars_flow:
    #                 if svf.name in DEFAULT_CONSTRUCTOR_CTX.keys():
    #                     # 如果流向了状态变量，将storage中该状态变量的初始值置为1，用以模拟构造函数的执行
    #                     default_addr = DEFAULT_CONSTRUCTOR_CTX[svf.name]
    #                     init_storage[sv_write_node.lvalue] = BitVecVal(int(default_addr, 16), 160)
