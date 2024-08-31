import time
from typing import List, Dict
import pandas as pd
import requests
from mysql.api import DatabaseApi


def save_all_txs() -> None:
    # 从CSV文件中读
    file_path = '/Users/mac/code/Gala-2.0/data/raw_contract.csv'
    df = pd.read_csv(file_path)
    db_api = DatabaseApi()

    last_to_addr = db_api.get_transaction_last_to_address()
    # res = db_api.get_transactions_by_contract_address(last_to_addr)
    # print(res)

    # 使用 iterrows() 遍历所有行
    reach_last_addr = False
    for row in df.itertuples(index=True):
        # 判断是否到达档案数据库中最后一条记录
        if last_to_addr and not reach_last_addr:
            if row.address == last_to_addr:
                reach_last_addr = True
            else:
                continue

        if row.txcount > 0:
            contract_name = row.name
            txs: List[Dict] = request_contract_txs(row.address)
            for tx in txs:
                # 过滤掉合约部署/创建的交易
                if tx["to"] == "":
                    continue
                txhash = tx["hash"]
                from_addr = tx["from"]
                to_addr = tx["to"]
                timeStamp = tx["timeStamp"]
                functionName = tx["functionName"]
                methodId = tx["methodId"]
                if from_addr and to_addr and timeStamp and functionName and methodId:
                    db_api.save_transaction(txhash, contract_name, from_addr, to_addr, int(timeStamp), functionName, methodId)
    return


def request_contract_txs(address: str):
    # 根据合约地址向Etherscan请求交易数据
    API_KEY = "HPXNN2GP4VFJIBD4USI8QJF6MFI75HRQZT"
    req_url = f"https://api.etherscan.io/api?" \
              f"module=account&" \
              f"action=txlist&" \
              f"address={address}&" \
              f"apikey={API_KEY}"
    for i in range(5):
        try:
            response = requests.get(req_url)
        except Exception as e:
            print(f"请求失败{e}，进入重试逻辑")
        else:
            time.sleep(0.1)
            break

    if response.status_code == 200:
        data = response.json()
        if data['status'] == '1':
            result = data['result']
            return result
        else:
            print("API请求失败：", "message: ", data['message'], "result: ", data['result'])
    else:
        print("API请求失败：", 'response.status_code ', response.status_code)


if __name__ == '__main__':
    save_all_txs()
