import time

from slither import Slither
from typing import Dict, Tuple, List, Set, FrozenSet

from slither.core.declarations import Function

from gala.symbolic import SymbolicExecResult
from gala.sequence import TxSeqGenerationResult, TxSequence
from gala.gala_runner import GalaRunner
from mysql.api import DatabaseApi
from permission.crucial_op_explorer import CrucialOpExplorer
from RQ.timeout import with_timeout, TimeoutException

API_KEY = "HPXNN2GP4VFJIBD4USI8QJF6MFI75HRQZT"


# ARMAN 0x63288968bd614fa5bfc695ff155583380b3dd63e
@with_timeout(60)
def test_contract_tx_seq_coverage(db_api: DatabaseApi, contract_address: str, name: str):
    contracts = Slither(target=contract_address, etherscan_api_key=API_KEY, disable_solc_warnings=True).get_contract_from_name(name)
    assert len(contracts) == 1
    contract = contracts[0]
    start_time = time.time()
    print(f"parse {contract.name}:{contract_address}")
    crucial_ops = CrucialOpExplorer().explore(contract)
    print("crucial ops explored")
    # GALA执行逻辑
    gala_runner = GalaRunner(contract)
    icfg = gala_runner.icfg_builder.build(main_contract=contract, program_points=crucial_ops)
    sliced_graph = gala_runner.icfg_slicer.slice(icfg=icfg)
    print("sliced graph built")
    gala_runner.taint_analyzer.analyze(sliced_graph)
    print("taint analyzer analyzed")
    GeneratedTxSequences = gala_runner.tx_sequence_generator.generate(sliced_graph)  # TODO bug
    end_time = time.time()
    time_cost = end_time - start_time
    # seq_count = 0
    # for slice_path_dict in GeneratedTxSequences.values():
    #     for slice_path, tx_seq_tuple in slice_path_dict.items():
    #         tx_seq_set: Set[TxSequence] = tx_seq_tuple[0]
    #         seq_count += len(tx_seq_set)
    # print(f"time_cost:{time_cost}, seq_num:{seq_count}, avg time per seq:{time_cost/seq_count}")

    print("tx sequences generated")
    real_tx_seq_coverage_list = test_generated_sequence_consistency(db_api, contract_address, GeneratedTxSequences)
    # 保存覆盖率
    # for from_addr, coverage_list in real_tx_seq_coverage_dict.items():
    #     total_tx = len(coverage_list)
    #     covered_tx = sum(1 for item in coverage_list if item[1])
    #     coverage = f"{(covered_tx / total_tx):.4f}"
    #     db_api.save_coverage(from_addr, contract_address, total_tx, coverage)
    #     print(f"save coverage for {from_addr}: {coverage}")

    for tx_seq_str, coverage_list in real_tx_seq_coverage_list.items():
        total_tx = len(coverage_list)
        covered_tx = sum(1 for item in coverage_list if item[1])
        coverage = f"{(covered_tx / total_tx):.4f}"
        db_api.save_txs_coverage(contract_address, total_tx, coverage, tx_seq_str)
        print(f"save coverage for {tx_seq_str, coverage}")


# res: SymbolicExecResult = gala_runner.symbolic_engine.execute(sliced_graph, GeneratedTxSequences)


def test_generated_sequence_consistency(db_api: DatabaseApi, contract_addr: str, generated_tx_sequences: TxSeqGenerationResult) -> \
        Dict[str, List[Tuple[str, bool]]]:
    # 检查生成的交易序列和实际交易序列的一致性
    real_tx_sequences: List[Tuple] = db_api.get_transactions_by_contract_address_group_by_from(contract_addr)
    # 1.构建一个dict，包含由不同用户发起的按照时间顺序排列的交易序列
    # 构建一个List[List],数组中的每一个元素是一个函数调用链, 每个元素不重复
    real_tx_seq_dict: Dict[str, List[str]] = dict()
    for tx in real_tx_sequences:
        from_addr = tx[2]
        pure_func_name = _extract_pure_func_name(tx[4])
        from_func_seq: List = real_tx_seq_dict.setdefault(from_addr, [])
        modify_state = tx[8]
        if modify_state == 0:  # 过滤掉所有的pure/view function
            continue
        if len(from_func_seq) == 0 or from_func_seq[-1] != pure_func_name:
            from_func_seq.append(pure_func_name)

    real_tx_seq_list: List[List[str]] = list()
    for tx_seq in real_tx_seq_dict.values():
        if tx_seq not in real_tx_seq_list:
            real_tx_seq_list.append(tx_seq)

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
    # # key:from_addr，Tuple[str, bool]:str:function name，bool：是否在生成集中
    # real_tx_seq_coverage_dict: Dict[str, List[Tuple[str, bool]]] = dict()
    # key: tx seq str(用->链接), value: 该tx seq每一个函数是否被覆盖
    real_tx_seq_coverage_list: Dict[str, List[Tuple[str, bool]]] = dict()
    for real_func_seq in real_tx_seq_list:
        for target_func_index in range(len(real_func_seq)):  # 被调用的函数
            is_covered = False
            target_func_name: str = real_func_seq[target_func_index]
            if target_func_name not in generated_tx_seq_dict:
                real_tx_seq_coverage_list.setdefault(_to_seq_str(real_func_seq), []).append((target_func_name, False))
                continue
            gen_target_func_seqs: Set[Tuple[str]] = generated_tx_seq_dict.get(target_func_name)
            # 情况1:在生成集中，存在直接调用该函数的序列，不需要前置条件
            is_covered = any(map(lambda s: len(s) == 1, gen_target_func_seqs))
            if is_covered:
                real_tx_seq_coverage_list.setdefault(_to_seq_str(real_func_seq), []).append((target_func_name, True))
                continue

            # 情况2:覆盖前置条件
            front_func_index = target_func_index - 1  # 前置函数的起始索引
            while front_func_index >= 0:
                # 获取所有前置的函数，并且去掉重复的函数名
                front_real_func_set: Set[str] = set(real_func_seq[front_func_index: target_func_index])
                for gen_func_seq in gen_target_func_seqs:
                    front_gen_func_seq: Tuple[str] = gen_func_seq[:-1]
                    # 判断是否所有的front_real_func_set被包含在front_gen_func_seq中(子集)
                    if front_real_func_set.issubset(front_gen_func_seq):
                        is_covered = True
                        break

                if is_covered:
                    break
                else:
                    front_func_index -= 1

            real_tx_seq_coverage_list.setdefault(_to_seq_str(real_func_seq), []).append((target_func_name, is_covered))

    return real_tx_seq_coverage_list


def test_RQ1():
    # 从数据库获取所有合约，对每个合约依次进行两个测试
    db_api = DatabaseApi()
    address_and_name_list = db_api.get_all_transact_contract_address_and_name()
    for addr_name in address_and_name_list:
        addr = addr_name[0]
        name = addr_name[1]
        # coverage_res = db_api.get_txs_coverage_by_contract_address(addr)
        # # 已经在数据库中被记录
        # if len(coverage_res) > 0:
        #     print(f"already processed contract:{name}")
        #     continue

        try:
            test_contract_tx_seq_coverage(db_api, addr, name)
        except Exception as e:
            if isinstance(e, TimeoutException):
                print(f"Timeout Exception:{addr}:{name}")
            else:
                print(f"Exception Contract:{name}:{addr}")
                print(e)


def _extract_pure_func_name(func_name: str):
    # 找到第一个左括号的索引
    left_parenthesis_index = func_name.find('(')

    # 如果找到了左括号，提取括号前的部分作为纯函数名
    if left_parenthesis_index != -1:
        pure_func_name = func_name[:left_parenthesis_index]
    else:
        pure_func_name = func_name  # 如果没有括号，则返回原始字符串

    return pure_func_name


def _to_seq_str(seq_list: List[str]):
    return "->".join(seq_list)


def calc_average_coverage():
    db_api = DatabaseApi()
    all_record_ids = db_api.get_all_coverage_ids()
    total_tx_num = 0
    total_covered_tx_num = 0
    for id in all_record_ids:
        coverage_info = db_api.get_coverage_by_id(id)
        tx_num = coverage_info[4]
        coverage = float(coverage_info[3])
        total_covered_tx_num += coverage * tx_num
        total_tx_num += tx_num

    average_coverage = f"{(total_covered_tx_num / total_tx_num):.4f}"
    print(average_coverage)



def calc_average_tx_coverage():
    db_api = DatabaseApi()
    all_record_ids = db_api.get_all_tx_coverage_ids()
    total_tx_num = 0
    total_covered_tx_num = 0
    for id in all_record_ids:
        coverage_info = db_api.get_tx_coverage_by_id(id)
        tx_num = coverage_info[2]
        if tx_num == 1:
            coverage = float(coverage_info[3])
            total_covered_tx_num += coverage * tx_num
            total_tx_num += tx_num

    average_coverage = f"{(total_covered_tx_num / total_tx_num):.4f}"
    print(average_coverage)


if __name__ == '__main__':
    test_RQ1()
    calc_average_tx_coverage()
