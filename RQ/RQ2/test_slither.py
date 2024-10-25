# 消融实验
from slither import Slither
from mysql.api import DatabaseApi
from slither.detectors.all_detectors import ArbitrarySendEth, ArbitrarySendErc20NoPermit, Suicidal
API_KEY = "HPXNN2GP4VFJIBD4USI8QJF6MFI75HRQZT"


def test_slither():
    db_api = DatabaseApi()
    all_verified_contracts = db_api.get_all_verified_pev_contract()
    for contract in all_verified_contracts:
        name = contract[1]
        address = contract[0]
        if contract[17] != 1:
            continue
        try:
            name = "basisneuro"
            address = "0x92949bd74c4d21852a3d9f7dfb841fad2833302b"
            print(f"Slither Analysis {name}:{address}")
            slither = Slither(target=address, etherscan_api_key=API_KEY, disable_solc_warnings=True)
            slither.register_detector(ArbitrarySendEth)
            slither.register_detector(ArbitrarySendErc20NoPermit)
            slither.register_detector(Suicidal)
            results = slither.run_detectors()
            print(results)
            # vul_num = 0
            # for res in results:
            #     vul_num += len(res)
            # verified_vul = contract[2]
            # if vul_num == 0:
            #     db_api.save_slither_verified_result(address, 0, 0, verified_vul)
            # elif vul_num < verified_vul:
            #     db_api.save_slither_verified_result(address, vul_num, 0, verified_vul - vul_num)
            # else:
            #     db_api.save_slither_verified_result(address, verified_vul, vul_num - verified_vul, 0)
            #     print(f"may be has FP")
        except Exception as e:
            db_api.save_slither_verified_result(address, -1, -1, -1)


if __name__ == '__main__':
    test_slither()
