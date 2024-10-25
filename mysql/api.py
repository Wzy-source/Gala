from . import client
from .client import DatabaseClient


class DatabaseApi:
    def __init__(self):
        self.client: DatabaseClient = DatabaseClient(host="localhost", port=3306, database="SmartContract", user="root", password="123456")

    # =======Transaction相关=========
    def get_transaction_last_to_address(self):
        self.client.check_connection()
        to_addr = self.client.get_last_to_address()
        return to_addr

    def get_all_transact_contract_address_and_name(self):
        self.client.check_connection()
        res = self.client.get_all_transact_contract_address_and_name()
        return res

    def get_transactions_by_contract_address_group_by_from(self, contract_addr):
        self.client.check_connection()
        # 统一将字符转为小写形式
        contract_addr = contract_addr.lower()
        return self.client.select_txs_by_contract_addr_group_by_from(contract_addr)

    # def get_transactions_by_contract_addr(self, contract_addr):
    #     self.client.check_connection()
    #     res = self.client.get_transactions_by_contract_addr(contract_addr)
    #     return res

    def save_transaction(self, txhash, contract_name, from_addr, to_addr, timeStamp, functionName, methodId):
        self.client.check_connection()
        # 统一将字符转为小写形式
        from_addr = from_addr.lower()
        to_addr = to_addr.lower()
        transaction_in = self.client.select_transaction_by_txhash(txhash)
        if transaction_in:
            print(f"当前交易已经保存在数据库：{contract_name, txhash}")
        else:
            print(f"已成功保存交易：{contract_name, txhash}")
            return self.client.save_transaction(txhash, contract_name, from_addr, to_addr, timeStamp, functionName, methodId)

    def set_func_modify_state(self, methodId, modify_state):
        self.client.check_connection()
        return self.client.set_function_modify_state_by_id(methodId, modify_state)

    def get_all_tx_ids(self):
        self.client.check_connection()
        return self.client.get_all_tx_ids()

    def get_tx_by_id(self, tx_id):
        self.client.check_connection()
        return self.client.get_tx_by_id(tx_id)

    # ========Coverage表相关==========
    def save_coverage(self, from_addr, to_addr, tx_num, coverage):
        from_addr = from_addr.lower()
        to_addr = to_addr.lower()

        self.client.save_coverage(from_addr, to_addr, tx_num, coverage)

        return

    def get_coverage_by_contract_address(self, contract_address):
        self.client.check_connection()
        contract_address = contract_address.lower()
        res = self.client.select_coverage_by_contract_address(contract_address)
        return res

    def get_all_coverage_ids(self):
        self.client.check_connection()
        res = self.client.get_all_coverage_ids()
        return res

    def get_coverage_by_id(self, id):
        self.client.check_connection()
        res = self.client.get_coverage_by_id(id)
        return res

    ## ========DetectionResult表相关==========
    def save_contract_address_name(self, address, name):
        self.client.check_connection()
        address = address.lower()
        return self.client.save_contract_address_and_name(address, name)

    def get_all_contract_address_and_name(self):
        self.client.check_connection()
        return self.client.get_all_contract_address_and_name()

    def save_detect_result_by_address(self, address):
        self.client.check_connection()
        address = address.lower
        pass

    def get_name_by_address(self, address):
        self.client.check_connection()
        address = address.lower()
        return self.client.get_name_by_address(address)

    def del_old_compiler_version_contracts(self, address):
        self.client.check_connection()
        address = address.lower()
        self.client.del_old_compiler_version_contracts(address)

    # ===========Txs Coverage===============
    def save_txs_coverage(self, contract_addr, tx_num, coverage, tx_seq_str):
        self.client.check_connection()
        contract_addr = contract_addr.lower()
        self.client.save_txs_coverage(contract_addr, tx_num, coverage, tx_seq_str)

    def get_txs_coverage_by_contract_address(self, contract_address):
        self.client.check_connection()
        contract_address = contract_address.lower()
        res = self.client.get_txseq_coverage_by_contract_address(contract_address)
        return res

    def get_all_tx_coverage_ids(self):
        self.client.check_connection()
        res = self.client.get_all_tx_coverage_ids()
        return res

    def get_tx_coverage_by_id(self, id):
        self.client.check_connection()
        res = self.client.get_tx_coverage_by_id(id)
        return res

    def save_compiler_version_in_verified_pev(self, version, address):
        self.client.check_connection()
        address = address.lower()
        res = self.client.save_compiler_version_in_verified_pev(version, address)
        return res

    def get_all_verified_pev_contract(self):
        self.client.check_connection()
        res = self.client.get_all_verified_pev_contract()
        return res

    def save_gala_verified_result(self, address, tp, fp, fn):
        self.client.check_connection()
        res = self.client.save_gala_verified_result(address, tp, fp, fn)
        return res

    def save_slither_verified_result(self, address, tp, fp, fn):
        self.client.check_connection()
        res = self.client.save_slither_verified_result(address, tp, fp, fn)
        return res

    # ===========raw contract============

    def get_all_raw_contract_ids(self):
        self.client.check_connection()
        res = self.client.get_all_raw_contract_ids()
        return res

    def get_raw_contract_by_id(self, id):
        self.client.check_connection()
        res = self.client.get_raw_contract_by_id(id)
        return res

    def save_raw_contract_detect_res_by_id(self, name_in, vul_num, id):
        self.client.check_connection()
        res = self.client.save_raw_contract_detect_res_by_id(name_in, vul_num, id)
        return res
