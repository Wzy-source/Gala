from gala.utils import SolcSwitcher, Settings
from slither.slither import Slither
from gala.gala_runner import GalaRunner
from permission.handlers import Handlers
from permission.crucial_op_explorer import CrucialOpExplorer

if __name__ == '__main__':
    # 解析设置
    settings = Settings(setting_path="/Users/mac/code/Gala-2.0/tests/Coinlancer/contract.json")
    SolcSwitcher.switch(settings.compiler_version)
    addr, name = settings.contract_address, settings.contract_name
    print("path:", settings.setting_path, "name:", settings.contract_name, "address:", settings.contract_address)
    # slither contract
    contract = Slither(target=settings.contract_path, disable_solc_warnings=True).get_contract_from_name(name)[0]
    crucial_ops = CrucialOpExplorer().explore(contract)
    # 运行Gala符号执行框架
    GalaRunner(contract).register_monitor_handlers(Handlers().get()).run(program_points=crucial_ops)
