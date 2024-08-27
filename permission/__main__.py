from gala.utils import SolcSwitcher, Settings
from slither.slither import Slither
from gala.gala_runner import GalaRunner
from permission.handlers import Handlers
from permission.crucial_op_explorer import CrucialOpExplorer
from permission.vul_checker import VulChecker

API_KEY = "HPXNN2GP4VFJIBD4USI8QJF6MFI75HRQZT"

if __name__ == '__main__':
    # 解析设置
    # settings = Settings(setting_path="/Users/mac/code/Gala-2.0/examples/simple_contract2.json")
    # SolcSwitcher.switch(settings.compiler_version)
    # addr, name = settings.contract_address, settings.contract_name
    # print("path:", settings.setting_path, "name:", settings.contract_name, "address:", settings.contract_address)
    # target = settings.contract_path  # 基于要编译的合约的文件路径
    target = "0x4c5057d1cc3642e9c3ac644133d88a20127fbd67"  # 基于合约地址
    name = "NFT20Pair"
    contracts = Slither(target=target, etherscan_api_key=API_KEY, disable_solc_warnings=True).get_contract_from_name(name)
    assert len(contracts) == 1, f"No Contract Or Multiple Contracts Named {name}"
    contract = contracts[0]
    crucial_ops = CrucialOpExplorer().explore(contract)
    # 运行Gala符号执行框架
    res = GalaRunner(contract).register_monitor_handlers(Handlers().get()).run(program_points=crucial_ops)
    # 输出执行结果
    VulChecker().check(contract.name, res)
