from typing import List, Tuple

from RQ.timeout import with_timeout
from mysql.api import DatabaseApi
from permission.vul_checker import PermissionVulChecker


def get_vul_contract_address_and_name(db_api: DatabaseApi) -> List[Tuple[str, str]]:
    all_detect_contract = db_api.get_all_contract_address_and_name()
    return all_detect_contract


@with_timeout(60)
def test_one_contract(address: str, name: str):
    crucial_ops, vul_res, intend_res = PermissionVulChecker().check(name, address)
    return crucial_ops, vul_res, intend_res


def test_all_raw_contracts():
    db_api = DatabaseApi()
    all_detected_contracts = get_vul_contract_address_and_name(db_api)
    all_raw_contract_ids = db_api.get_all_raw_contract_ids()
    for raw_contract_id in all_raw_contract_ids:
        raw_contract = db_api.get_raw_contract_by_id(raw_contract_id)
        # if raw_contract[8] is not None:
        #     continue
        if not raw_contract[3].startswith('0.4.') and not raw_contract[3].startswith('0.5.') and not raw_contract[3].startswith('0.6.'):
            continue
        raw_name = raw_contract[2]
        raw_address = raw_contract[1]
        is_name_in = any((raw_name == dc[1] and raw_address != dc[0]) for dc in all_detected_contracts)
        print(f"=========Analysis Begin: {raw_name}:{raw_address}=========")
        try:
            crucial_ops, vul_res, intend_res = test_one_contract(raw_address, raw_name)
            vul_num = len(vul_res.keys())
            db_api.save_raw_contract_detect_res_by_id(is_name_in, vul_num, raw_contract_id)
            print(f"=========Analysis Success: {raw_name}:{raw_address}=========")
        except Exception as e:
            db_api.save_raw_contract_detect_res_by_id(is_name_in, -1, raw_contract_id)
            print(f"=========Analysis Failed: {raw_name}:{raw_address}=========")


if __name__ == '__main__':
    test_all_raw_contracts()
