from slither import Slither
from typing import Dict, Tuple, List, Set, FrozenSet

from slither.core.declarations import Function

from gala.symbolic import SymbolicExecResult
from gala.sequence import TxSeqGenerationResult, TxSequence
from gala.gala_runner import GalaRunner
from mysql.api import DatabaseApi
from permission.crucial_op_explorer import CrucialOpExplorer

API_KEY = "HPXNN2GP4VFJIBD4USI8QJF6MFI75HRQZT"


def test_one_contract(address: str, name: str):
    contracts = Slither(target=address, etherscan_api_key=API_KEY, disable_solc_warnings=True).get_contract_from_name(name)
    assert len(contracts) == 1
    contract = contracts[0]
    crucial_ops = CrucialOpExplorer().explore(contract)
    db_api = DatabaseApi()
    # GALA执行逻辑
    gala_runner = GalaRunner(contract)
    icfg = gala_runner.icfg_builder.build(main_contract=contract, program_points=crucial_ops)
    sliced_graph = gala_runner.icfg_slicer.slice(icfg=icfg)
    gala_runner.taint_analyzer.analyze(sliced_graph)
    GeneratedTxSequences = gala_runner.tx_sequence_generator.generate(sliced_graph)
    real_tx_seq_coverage_map = test_generated_sequence_consistency(db_api, address, GeneratedTxSequences)
    # res: SymbolicExecResult = gala_runner.symbolic_engine.execute(sliced_graph, GeneratedTxSequences)


def test_generated_sequence_consistency(db_api: DatabaseApi, contract_addr: str, generated_tx_sequences: TxSeqGenerationResult) -> \
        Dict[str, Dict[FrozenSet[str], bool]]:
    # 检查生成的交易序列和实际交易序列的一致性
    real_tx_sequences: List[Tuple] = db_api.get_transactions_by_contract_address_group_by_from(contract_addr)
    # 1.构建一个dict，包含由不同用户发起的按照时间顺序排列的交易序列
    real_tx_seq_dict: Dict[str, List[str]] = dict()
    for tx in real_tx_sequences:
        from_addr = tx[2]
        pure_func_name = _extract_pure_func_name(tx[4])
        from_func_seq: List = real_tx_seq_dict.setdefault(from_addr, [])
        if len(from_func_seq) == 0 or from_func_seq[-1] != pure_func_name:
            from_func_seq.append(pure_func_name)

    # 2.构建一个字典，key是最后一个交易的名称，value是所有包含最后一个交易的交易序列
    generated_tx_seq_dict: Dict[str, Set[Tuple[str]]] = dict()
    for slice_path_dict in generated_tx_sequences.values():
        for slice_path, tx_seq_tuple in slice_path_dict.items():
            target_func: Function = slice_path.slice_func
            tx_seq_set: Set[TxSequence] = tx_seq_tuple[0]
            func_seq_set: Set[Tuple[str]] = set()
            for tx_seq in tx_seq_set:
                from_func_seq: Tuple = tuple(map(lambda x: x.function.name, tx_seq.txs))
                func_seq_set.add(from_func_seq)
            generated_tx_seq_dict.setdefault(target_func.name, func_seq_set)

    # 目前先只判断在生成集中含有的函数（key），不考虑target_func_name not in generated_tx_seq_dict的情况
    # key:str: 需要被trigger的函数，Set[str]前置函数，bool：是否在生成集中
    real_tx_seq_coverage_map: Dict[str, Dict[FrozenSet[str], bool]] = dict()
    for from_addr, real_func_seq in real_tx_seq_dict.items():
        for target_func_index in range(len(real_func_seq)):  # 被调用的函数
            is_covered = False
            front_func_set: Set[str] = set()
            target_func_name: str = real_func_seq[target_func_index]
            if target_func_name not in generated_tx_seq_dict:
                continue
            gen_target_func_seqs: Set[Tuple[str]] = generated_tx_seq_dict.get(target_func_name)
            if target_func_index == 0:  # 判断被调用的函数是否直接存在于生成的交易序列中
                for gen_func_seq in gen_target_func_seqs:
                    if len(gen_func_seq) == 1 and gen_func_seq[0] == target_func_name:
                        is_covered = True
                        break
            else:
                front_func_index = target_func_index - 1  # 前置函数的起始索引
                while front_func_index >= 0:
                    # 获取所有前置的函数，并且去掉重复的函数名
                    front_real_func_set: Set[str] = set(real_func_seq[front_func_index: target_func_index])
                    for gen_func_seq in gen_target_func_seqs:
                        front_gen_func_seq: Tuple[str] = gen_func_seq[:-1]
                        # 判断是否所有的front_real_func_set被包含在front_gen_func_seq中(子集)
                        if front_real_func_set.issubset(front_gen_func_seq):
                            is_covered = True
                            front_func_set = front_real_func_set
                            break

                    if is_covered:
                        break
                    else:
                        front_func_index -= 1

            real_tx_seq_coverage_map.setdefault(target_func_name, dict()).setdefault(frozenset(front_func_set), is_covered)

    return real_tx_seq_coverage_map


def test_sequence_execution_efficiency():
    pass


def test_RQ1():
    # 从数据库获取所有合约，对每个合约依次进行两个测试
    test_one_contract("0x000000004a434312bfcbb119fa7bbdf7169fdc56", "AlcxVault")


def _extract_pure_func_name(func_name: str):
    # 找到第一个左括号的索引
    left_parenthesis_index = func_name.find('(')

    # 如果找到了左括号，提取括号前的部分作为纯函数名
    if left_parenthesis_index != -1:
        pure_func_name = func_name[:left_parenthesis_index]
    else:
        pure_func_name = func_name  # 如果没有括号，则返回原始字符串

    return pure_func_name


if __name__ == '__main__':
    test_RQ1()
