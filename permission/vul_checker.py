from gala import DEFAULT_DEPLOYER_CTX, DEFAULT_ATTACKER_CTX
from gala.symbolic import SymbolicExecResult, SymbolicState, Deployer_Addr, Attacker_Addr
from gala.sequence import TxSequence, Transaction
from gala.graph import ICFGNode
from z3 import ModelRef, BitVecRef, BitVecNumRef, ExprRef
from typing import List, Tuple, FrozenSet, Union
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


class VulChecker:
    def __init__(self):
        pass

    def check(self, contract_name: str, sym_exec_res: SymbolicExecResult) -> None:
        for program_points, tx_seq_exec_res in sym_exec_res.items():
            seq_func_ctx_record: List[List[Tuple[Function, dict]]] = []
            for tx_seq, exec_res in tx_seq_exec_res.items():
                is_feasible, model, state_list = exec_res
                # 如果已经判断为安全的，则不需要再进一步检查
                if not is_feasible:
                    continue
                # 过滤掉user-intended patterns
                # if self.filter_user_intended_patterns(program_points, model, state_list):
                #     continue
                # 判断之前是否已经输出过该交易序列（不考虑具体的执行流（Slice），而是以函数为粒度进行输出）
                func_ctx_seq: List[Tuple[Function, dict]] = self.generate_func_ctx_seq(state_list)
                if func_ctx_seq in seq_func_ctx_record:
                    continue
                else:
                    seq_func_ctx_record.append(func_ctx_seq)
                # 输出潜在的漏洞信息
                self.log_one_vul_result(program_points, model, state_list, contract_name)

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

    def log_one_vul_result(self, program_points: FrozenSet[ICFGNode], model: ModelRef, state_list: List[SymbolicState], contract_name: str):
        print()
        print(
            f"{RED}[ PRIVILEGE ESCALATION VULNERABILITY FOUND FOR {contract_name} CONTRACT ]{RESET}")
        # 输出攻击者和部署者的地址
        print(f"Default Deployer: {Deployer_Addr} ({int(Deployer_Addr, 16)})")
        print(f"Default Attacker: {Attacker_Addr} ({int(Attacker_Addr, 16)})")
        print(f"{CYAN}====> Program Points <===={RESET}")
        [print(str(pn)) for pn in program_points]
        # 输出权限集对应的交易序列和调用者信息
        print(f"{CYAN}====> Generated Tx Sequence <===={RESET}")
        tx_seq_str = "[Deployer] constructor"
        for state in state_list:
            # 判断约束求解器中model中的解是
            tx_func_name = state.tx.function
            contract_name = state.tx.function.contract_declarer
            sender_val = self.get_sender_value(state.ctx["msg.sender"], model)
            sender_name = "Deployer" if sender_val == int(Deployer_Addr, 16) else "Attacker"
            tx_seq_str += f" -> [{sender_name}] {contract_name}.{tx_func_name}"

        print(tx_seq_str)

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
