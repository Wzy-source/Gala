from RQ.timeout import with_timeout, TimeoutException
from permission.vul_checker import PermissionVulChecker
from mysql.api import DatabaseApi
from typing import List


def test_RQ2():
    # 从数据库中读取数据
    db_api = DatabaseApi()
    contract_address_name_list: List[str, str] = db_api.get_all_contract_address_and_name()
    # 运行Gala，对GT数据集进行验证
    for address_name in contract_address_name_list:
        address = address_name[0]
        name = address_name[1]
        try:
            test_one_contract(address, name)
        except Exception as e:
            if isinstance(e, TimeoutException):
                print("Time Out Error")
            print(f"Analysis Error:{name}:{address}")


@with_timeout(60)
def test_one_contract(address: str, name: str):
    PermissionVulChecker().check(name, address)


if __name__ == '__main__':
    # test_RQ2()
    address = "0x08ade307321221677e837c8150bdbd4e891daf09"
    name = "Vault"
    test_one_contract(address, name)
