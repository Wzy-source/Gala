from enum import Enum, auto

from slither import Slither

from gala import DEFAULT_DEPLOYER_CTX, DEFAULT_ATTACKER_CTX
from gala.gala_runner import GalaRunner
from gala.symbolic import SymbolicExecResult, SymbolicState, Deployer_Addr, Attacker_Addr
from gala.sequence import TxSequence, Transaction
from gala.graph import ICFGNode
from z3 import ModelRef, BitVecRef, BitVecNumRef, ExprRef
from typing import List, Tuple, FrozenSet, Union, Dict
from slither.core.declarations import Function
from .crucial_op_explorer import CrucialOpExplorer

# ANSI 转义码
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
RESET = "\033[0m"
BRIGHT_RED = "\033[91;1m"

API_KEY = "HPXNN2GP4VFJIBD4USI8QJF6MFI75HRQZT"


class VulFlag(Enum):
    VULNERABLE = auto()
    INTENDED = auto()


class PermissionVulChecker:
    def __init__(self):
        pass

    def check(self, name: str, address: str):
        slither = Slither(target=address, etherscan_api_key=API_KEY, disable_solc_warnings=True)
        if len(slither.contracts) > 6:
            raise Exception("Too many contracts")
        main_contract = slither.get_contract_from_name(name)
        assert len(main_contract) == 1, f"No Contract Or Multiple Contracts Named {name}"
        main_contract = main_contract[0]
        crucial_ops = CrucialOpExplorer().explore(main_contract)
        # 运行Gala符号执行框架
        sym_exec_res = GalaRunner(main_contract).run(program_points=crucial_ops)
        # 对符号执行结果进行判断
        vul_res, intend_res = self.check_and_log_vul_by_sym_res(name, address, sym_exec_res)
        return crucial_ops, vul_res, intend_res

    def check_and_log_vul_by_sym_res(self, name: str, address: str, sym_exec_res: SymbolicExecResult):
        # 对符号执行结果进行判断
        vul_res_to_log_list: List[Tuple[FrozenSet[ICFGNode], List[Tuple[str, str, str]]]] = []
        intended_res_to_log_list: List[Tuple[FrozenSet[ICFGNode], List[Tuple[str, str, str]]]] = []
        for program_points, tx_seq_exec_res in sym_exec_res.items():
            seq_func_ctx_record: List[List[Tuple[Function, dict]]] = []
            for tx_seq, exec_res in tx_seq_exec_res.items():
                is_feasible, model, state_list = exec_res
                # 如果已经判断为安全的，则不需要再进一步检查
                if not is_feasible:
                    continue
                # 过滤掉user-intended patterns
                if self.filter_user_intended_patterns(program_points, model, state_list):
                    continue
                # 判断之前是否已经输出过该交易序列（不考虑具体的执行流（Slice），而是以函数为粒度进行输出）
                func_ctx_seq: List[Tuple[Function, dict]] = self.generate_func_ctx_seq(state_list)
                if func_ctx_seq in seq_func_ctx_record:
                    continue
                else:
                    seq_func_ctx_record.append(func_ctx_seq)
                # 输出潜在的漏洞信息
                may_be_intended, func_call_seq = self.generate_func_call_seq(model, state_list)
                if may_be_intended:
                    intended_res_to_log_list.append((program_points, func_call_seq))
                else:
                    vul_res_to_log_list.append((program_points, func_call_seq))

        vul_res = self.log_detect_result(VulFlag.VULNERABLE, vul_res_to_log_list, name, address)
        intend_res = self.log_detect_result(VulFlag.INTENDED, intended_res_to_log_list, name, address)
        return vul_res, intend_res

    def filter_user_intended_patterns(self, program_points: FrozenSet[ICFGNode], model: ModelRef, state_list: List[SymbolicState]) -> bool:
        # 第一种： 如果存在transferOwnership操作/对owner的赋值操作的交易是由owner本人执行的
        for state in state_list:
            for op in state.tx.exec_path.nodes:
                if CrucialOpExplorer.is_ownership_transfer_op(op):
                    sender_val = self.get_sender_value(state.ctx["msg.sender"], model)
                    if sender_val == int(Deployer_Addr, 16):  # 如果是由于部署者转移了ownership，说明是刻意的行为
                        return True
        return False

    @staticmethod
    def generate_func_ctx_seq(state_list: List[SymbolicState]) -> List[Tuple[Function, dict]]:
        func_ctx_seq = []
        for state in state_list:
            func = state.tx.function
            ctx = state.ctx
            func_ctx_seq.append((func, ctx))
        return func_ctx_seq

    def generate_func_call_seq(self, model: ModelRef, state_list: List[SymbolicState]) -> Tuple[bool, List[Tuple[str, str, str]]]:
        # 生成函数调用序列，判断每一个函数的caller是谁
        func_call_seq = []
        may_be_user_intend = False
        for state in state_list:
            func_name = state.tx.function.name
            contract_name = state.tx.function.contract_declarer
            sender_val = self.get_sender_value(state.ctx["msg.sender"], model)
            sender_name = "Deployer" if sender_val == int(Deployer_Addr, 16) else "Attacker"
            if sender_name == "Deployer":
                may_be_user_intend = True
            func_call_seq.append((sender_name, contract_name, func_name))
        return may_be_user_intend, func_call_seq

    @staticmethod
    def log_detect_result(vul_flag: VulFlag, res_to_log_list: List[Tuple[FrozenSet[ICFGNode], List[Tuple[str, str, str]]]], contract_name: str,
                          contract_address: str):
        # 对输出的函数序列进行分组,对漏洞进行溯源：找到最短交易序列的集合
        grouped_sequence_map: Dict[str, List[Tuple[FrozenSet[ICFGNode], str]]] = dict()
        for one_vul_res in res_to_log_list:
            # res_to_log_list： program points + func_call_seq(Sender-Contract-Function)
            program_points, func_call_seq = one_vul_res
            # 拼接交易序列字符串
            tx_seq_str = "Deployer: [Default Constructors]"
            for func_call_info in func_call_seq:
                sender_name, contract_name, tx_func_name = func_call_info
                if contract_name:
                    tx_seq_str += f" -> {sender_name}: [{contract_name}.{tx_func_name}]"
                else:
                    tx_seq_str += f" -> {sender_name}: [{tx_func_name}]"

            # Create a list of current keys to iterate over
            root_seq_keys = list(grouped_sequence_map.keys())
            root_found = False
            root_replaced = False
            for root_seq in root_seq_keys:
                # 如果当前序列是某个已有根因序列的扩展，说明可以归为该根因
                if tx_seq_str.startswith(root_seq):
                    grouped_sequence_map[root_seq].append((program_points, tx_seq_str))
                    root_found = True
                    break
                # 如果当前的根因是当前序列的拓展，可以将根因的值加入到当前序列，然后将根因删除
                elif root_seq.startswith(tx_seq_str):
                    root_replaced = True
                    root_seq_list = grouped_sequence_map[root_seq]
                    grouped_sequence_map.setdefault(tx_seq_str, []).extend(root_seq_list)
                    del grouped_sequence_map[root_seq]

            if (not root_found) or root_replaced:
                grouped_sequence_map.setdefault(tx_seq_str, []).append((program_points, tx_seq_str))

        for root_seq, grouped_sequences in grouped_sequence_map.items():
            if vul_flag == VulFlag.VULNERABLE:
                print(f"{RED}[ PRIVILEGE ESCALATION VULNERABILITY FOUND FOR {contract_name}:{contract_address} ]{RESET}")
            else:
                print(f"{GREEN}[ MAY BE INTENDED BEHAVIOR, BUT NEED ATTENTION {contract_name}:{contract_address} ]{RESET}")

            print(f"{CYAN}====> Root Tx Sequence <===={RESET}")
            print(f"{YELLOW}{root_seq}{RESET}")
            print(f"{CYAN}====> Vul Sequences Start With Root Tx Sequence <===={RESET}")
            for gs_info_index in range(len(grouped_sequences)):
                gs_info = grouped_sequences[gs_info_index]
                program_points, tx_seq_str = gs_info
                print(f"{CYAN}====> Generated Vul Sequences {gs_info_index + 1} and Program Points <===={RESET}")
                [print(str(pn)) for pn in program_points]
                print(f"<Vul Sequences> {tx_seq_str}")
            print()

        return grouped_sequence_map

    @staticmethod
    def get_sender_value(sym_sender: ExprRef, model: ModelRef) -> int:
        # ❌使用Model来判断是有问题的：
        # 每一次Check的Model只是局部的可满足解，不一定是全局的可满足解
        # 比如0x4c5057d1cc3642e9c3ac644133d88a20127fbd67合约的init -> setParam方法
        # 两种情况：1.sym_sender是具体值，则直接返回具体的int类型整数
        # 2.sym_sender是符号值，则通过model找具体的解，返回符号值
        if isinstance(sym_sender, BitVecNumRef):
            return sym_sender.as_long()
        else:
            return model[sym_sender].as_long()
