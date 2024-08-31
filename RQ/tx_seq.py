from slither import Slither

from gala import SymbolicExecResult, TxSeqGenerationResult
from gala.gala_runner import GalaRunner
from mysql.api import DatabaseApi
from permission.crucial_op_explorer import CrucialOpExplorer

API_KEY = "HPXNN2GP4VFJIBD4USI8QJF6MFI75HRQZT"


def test_generated_sequence_consistency(db_api: DatabaseApi, address: str, generated_tx_sequence: TxSeqGenerationResult):
    # 检查生成的交易序列和世纪交易序列的一致性
    contract_txs = db_api.get_transactions_by_contract_address(address)
    


def test_sequence_execution_efficiency():
    pass


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
    # TODO 验证序列的一致性
    test_generated_sequence_consistency(db_api, address, GeneratedTxSequences)
    res: SymbolicExecResult = gala_runner.symbolic_engine.execute(sliced_graph, GeneratedTxSequences)


def test_RQ1():
    pass


if __name__ == '__main__':
    test_RQ1()
