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

    def select_transaction(self, txhash):
        sql = "SELECT * FROM Transaction WHERE txhash=%s;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, txhash)
        self.__client.commit()
        result = cursor.fetchone()
        return result

    def get_last_to_address(self):
        sql = "SELECT `to` FROM Transaction ORDER BY id DESC LIMIT 1;"
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql)
        result = cursor.fetchone()
        return result[0] if result is not None else None  # Assuming `to` is the first column in the result

    def save_coverage(self, from_addr, to_addr, coverage, tx_num):
        sqp = "INSERT INTO Coverage (from_addr, to_addr,tx_num, coverage) VALUES (%s,%s,%s,%s);"
        values = (from_addr, to_addr, tx_num, coverage)
        cursor: Cursor = self.__client.cursor()
        cursor.execute(sqp, values)
        self.__client.commit()
        return self.__client.insert_id()

    def select_txs_by_contract_addr_group_by_from(self, to_addr):
        sql = "SELECT * FROM Transaction WHERE `to` = %s ORDER BY `from`, timeStamp ASC;"

        cursor: Cursor = self.__client.cursor()
        cursor.execute(sql, to_addr)

        # Fetch all results
        result = cursor.fetchall()

        # Commit any pending transactions, though this should just be a read operation
        self.__client.commit()

        return result  # Returning the list of grouped and sorted transact

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

    def __del__(self):
        self.close_connect()

    def __init_client(self) -> pymysql.Connection:
        return pymysql.connect(host=self.__host, port=self.__port, database=self.__database,
                               user=self.__user, password=self.__password)
