import pymysql
from pymysql.cursors import Cursor


class DatabaseClient:
    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.__host: str = host
        self.__port: int = port
        self.__database: str = database
        self.__user: str = user
        self.__password: str = password
        self.__client: pymysql.Connection = self.__init_client()

    def save_transaction(self, txhash, name, from_addr, to_addr, timeStamp, functionName, methodId) -> int:
        sql = """
        INSERT INTO Transaction (txhash,name,`from`, `to`, functionName, methodId, timeStamp)
        VALUES (%s,%s,%s, %s, %s, %s, %s)
        """
        values = (txhash, name, from_addr, to_addr, functionName, methodId, timeStamp)
        cursor: Cursor = self.__client.cursor()
        try:
            cursor.execute(sql, values)
        except Exception as e:
            print(e)
        ret = self.__client.insert_id()
        self.__client.commit()
        return ret

    def select_transaction_by_txhash(self, txhash):
        sql = "SELECT * FROM Transaction WHERE txhash=%s;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, txhash)
        self.__client.commit()
        result = cursor.fetchone()
        return result

    def get_transactions_by_contract_addr(self, to_addr):
        sql = "SELECT * FROM Transaction WHERE `to`=%s;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, to_addr)
        self.__client.commit()
        result = cursor.fetchall()
        return self.__extract_all_from_tuple(result)

    def get_all_transact_contract_address_and_name(self):
        sql = "SELECT DISTINCT `to`,name FROM Transaction;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql)
        self.__client.commit()
        result = cursor.fetchall()
        return self.__extract_all_from_tuple(result)

    def get_last_to_address(self):
        sql = "SELECT `to` FROM Transaction ORDER BY id DESC LIMIT 1;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql)
        result = cursor.fetchone()
        return result[0] if result is not None else None  # Assuming `to` is the first column in the result

    def save_coverage(self, from_addr, to_addr, tx_num, coverage):
        sql = """
        INSERT INTO Coverage (`from`, `to`, tx_num, coverage)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE tx_num = VALUES(tx_num), coverage = VALUES(coverage);
        """
        values = (from_addr, to_addr, tx_num, coverage)
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, values)
        self.__client.commit()
        return self.__client.insert_id()

    def select_coverage_by_contract_address(self, contract_address):
        sql = """
        SELECT coverage FROM Coverage WHERE  `to`=%s;
        """
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, contract_address)
        self.__client.commit()
        result = cursor.fetchall()
        return self.__extract_all_from_tuple(result)

    def get_all_coverage_ids(self):
        sql = "SELECT `id` FROM Coverage;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql)
        self.__client.commit()
        result = cursor.fetchall()
        return self.__extract_all_from_tuple(result)

    def get_coverage_by_id(self, id):
        sql = "SELECT * FROM Coverage WHERE `id`=%s;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, id)
        self.__client.commit()
        result = cursor.fetchone()
        return result

    def select_txs_by_contract_addr_group_by_from(self, to_addr):
        sql = "SELECT * FROM Transaction WHERE `to` = %s ORDER BY `from`, timeStamp ASC;"

        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, to_addr)

        # Fetch all results
        result = cursor.fetchall()

        # Commit any pending transactions, though this should just be a read operation
        self.__client.commit()

        return self.__extract_all_from_tuple(result)  # Returning the list of grouped and sorted transact

    def set_function_modify_state_by_id(self, methodId, modify_state):
        sql = "UPDATE Transaction SET modify_state=%s WHERE methodId=%s;"
        values = (modify_state, methodId)
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, values)
        self.__client.commit()
        return self.__client.insert_id()

    def get_all_tx_ids(self):
        sql = "SELECT `id` FROM Transaction;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql)
        self.__client.commit()
        result = cursor.fetchall()
        return self.__extract_all_from_tuple(result)

    def get_tx_by_id(self, id):
        sql = "SELECT * FROM Transaction WHERE `id`=%s;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, id)
        self.__client.commit()
        result = cursor.fetchone()
        return result

    def save_contract_address_and_name(self, address, name):
        sql = """INSERT INTO DetectionResult (address, name)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE name = VALUES(name);
        """
        values = (address, name)
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, values)
        self.__client.commit()
        return self.__client.insert_id()

    def get_all_contract_address_and_name(self):
        sql = "SELECT address,name FROM DetectionResult;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        self.__client.commit()
        return self.__extract_all_from_tuple(result)

    def get_name_by_address(self, address):
        sql = "SELECT name FROM DetectionResult WHERE address=%s;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, address)
        result = cursor.fetchone()
        return result[0] if result is not None else None

    def get_all_untest_contract_address_and_name(self):
        sql = "SELECT address,name FROM DetectionResult WHERE Gala IS NULL;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        self.__client.commit()
        return self.__extract_all_from_tuple(result)

    def save_gala_result(self, address, result):
        sql = """
        INSERT INTO DetectionResult (address, Gala)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE Gala = VALUES(Gala);
        """
        values = (address, result)
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, values)
        self.__client.commit()
        return self.__client.insert_id()

    def del_old_compiler_version_contracts(self, address):
        sql = "DELETE FROM DetectionResult WHERE address=%s;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, address)
        self.__client.commit()



    # =======Txs Coverage=========
    def save_txs_coverage(self,contract_addr,tx_num,coverage,tx_seq_str):
        sql = "INSERT INTO TxsCoverage (contract_addr, tx_num, coverage, tx_seq_str) VALUES (%s, %s, %s,%s)"
        values = (contract_addr, tx_num, coverage, tx_seq_str)
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, values)
        self.__client.commit()
        return self.__client.insert_id()


    def get_txseq_coverage_by_contract_address(self, contract_addr):
        sql = "SELECT * FROM TxsCoverage WHERE contract_addr=%s;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, contract_addr)
        result = cursor.fetchall()
        return self.__extract_all_from_tuple(result)


    def get_all_tx_coverage_ids(self):
        sql = "SELECT id FROM TxsCoverage;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        return self.__extract_all_from_tuple(result)


    def get_tx_coverage_by_id(self,id):
        sql = "SELECT * FROM TxsCoverage WHERE id=%s;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, id)
        result = cursor.fetchone()
        return result


    def is_open(self):
        if self.__client is not None:
            try:
                self.__client.ping(reconnect=False)
                return True
            except Exception:
                return False
        return False

    def open_connect(self):
        self.__client = self.__init_client()

    def close_connect(self):
        if self.is_open():
            self.__client.close()

    def check_connection(self):
        if not self.is_open():
            self.open_connect()

    def __extract_all_from_tuple(self, t: tuple) -> list:
        ret: list = []
        for item in t:
            ret.append(item)
        return ret

    def __del__(self):
        self.close_connect()

    def __init_client(self) -> pymysql.Connection:
        return pymysql.connect(host=self.__host, port=self.__port, database=self.__database,
                               user=self.__user, password=self.__password)
