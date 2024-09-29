import sys

from gala.utils import SolcSwitcher, Settings
from slither.slither import Slither
from gala.gala_runner import GalaRunner
from permission.handlers import Handlers
from permission.crucial_op_explorer import CrucialOpExplorer

from .vul_checker import PermissionVulChecker

API_KEY = "HPXNN2GP4VFJIBD4USI8QJF6MFI75HRQZT"

if __name__ == '__main__':
    # 解析设置
    settings = Settings(setting_path="/Users/mac/code/Gala-2.0/examples/simple_contract.json")
    SolcSwitcher.switch(settings.compiler_version)
    addr, name = settings.contract_address, settings.contract_name
    print("path:", settings.setting_path, "name:", settings.contract_name, "address:", settings.contract_address)
    target = settings.contract_path  # 基于要编译的合约的文件路径
    # target = "0x4c5057d1cc3642e9c3ac644133d88a20127fbd67"  # 基于合约地址
    # name = "NFT20Pair"
    PermissionVulChecker().check(name, target)
