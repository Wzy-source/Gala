from .client import DatabaseClient


class DatabaseApi:
    def __init__(self):
        self.client: DatabaseClient = DatabaseClient(host="localhost", port=3306, database="SmartContract", user="root", password="123456")

    # =======Transaction相关=========
    def get_transaction_last_to_address(self):
        self.client.check_connection()
        to_addr = self.client.get_last_to_address()
        return to_addr

    def save_transaction(self, txhash, contract_name, from_addr, to_addr, timeStamp, functionName, methodId):
        self.client.check_connection()
        # 统一将字符转为小写形式
        from_addr = from_addr.lower()
        to_addr = to_addr.lower()
        transaction_in = self.client.select_transaction(txhash)
        if transaction_in:
            print(f"当前交易已经保存在数据库：{contract_name, txhash}")
        else:
            print(f"已成功保存交易：{contract_name, txhash}")
            return self.client.save_transaction(txhash, contract_name, from_addr, to_addr, timeStamp, functionName, methodId)

    # ========Coverage表相关==========
    def save_coverage(self, from_addr, to_addr, coverage, tx_num):
        return self.client.save_coverage(from_addr, to_addr, tx_num, coverage)

    def get_transactions_by_contract_address(self, contract_addr):
        self.client.check_connection()
        # 统一将字符转为小写形式
        contract_addr = contract_addr.lower()
        return self.client.select_txs_by_contract_addr_group_by_from(contract_addr)
