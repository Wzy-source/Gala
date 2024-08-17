from gala.utils import SolcSwitcher, Settings
from slither.slither import Slither
from gala.gala_runner import GalaRunner

if __name__ == '__main__':
    settings = Settings(setting_path="/Users/mac/code/Gala-2.0/tests/MorphToken/contract.json")
    SolcSwitcher.switch_solc(settings.compiler_version)
    addr, name = settings.contract_address, settings.contract_name
    print("path:", settings.setting_path, "name:", settings.contract_name, "address:", settings.contract_address)
    contract = Slither(target=settings.contract_path, disable_solc_warnings=True).get_contract_from_name(name)[0]
    GalaRunner().run(main_contract=contract)
