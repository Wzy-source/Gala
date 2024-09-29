from slither import Slither
from slither.core.declarations import Contract

from mysql.api import DatabaseApi

API_KEY = "HPXNN2GP4VFJIBD4USI8QJF6MFI75HRQZT"

def filter():
    db_api = DatabaseApi()
    contract_address_names = db_api.get_all_contract_address_and_name()
    for addr_name in contract_address_names:
        addr = addr_name[0]
        name = addr_name[1]
        try:
            slither = Slither(target=addr, etherscan_api_key=API_KEY)
            target: Contract = slither.get_contract_from_name(name)[0]
            version = target.compilation_unit.compiler_version.version
            if version.startswith("0.4"):
                pass
            elif version.startswith("0.3") or version.startswith("0.2") or version.startswith("0.1"):
                db_api.del_old_compiler_version_contracts(addr)
                print(f"deleted old compiler version: {name}:{addr}")
        except Exception as e:
            print(e)


if __name__ == '__main__':
    filter()
