import json
import time
from typing import List, Dict
import pandas as pd
import requests
from mysql.api import DatabaseApi


def save_all_vulnerable_contract_txs() -> None:
    # 从CSV文件中读
    file_path = '/Users/mac/code/Gala-2.0/data/vulnerable_contract.csv'
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

        if row is not None:
            # 根据地址获取名称
            contract_name = db_api.get_name_by_address(row.address)
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


def set_func_modify_state():
    db_api = DatabaseApi()
    all_tx_ids = db_api.get_all_tx_ids()
    for tx_id in all_tx_ids:
        tx = db_api.get_tx_by_id(tx_id)
        if tx[8] is not None:
            continue
        # 向Etherscan请求API
        abi_str = request_contract_abi(tx[3])
        abi = json.loads(abi_str)
        function_pure_name = _extract_pure_func_name(tx[4])
        modify_state = True
        # 判断是否是pure/view
        print(f"func name:{function_pure_name}, contract address:{tx[3]}")
        for func_item in abi:
            if 'name' in func_item and func_item['name'] == function_pure_name:
                if 'stateMutability' in func_item and (func_item['stateMutability'] == "view" or func_item['stateMutability'] == "pure"):
                    modify_state = False
                    break
        # 更新交易
        db_api.set_func_modify_state(tx[5], modify_state)
        print(f"func name:{function_pure_name}, is view/pure:{False if modify_state else True}")


def request_contract_abi(address: str):
    API_KEY = "HPXNN2GP4VFJIBD4USI8QJF6MFI75HRQZT"
    url = (f"https://api.etherscan.io/api?"
           f"module=contract&"
           f"action=getabi&"
           f"address={address}"
           f"&apikey={API_KEY}")
    for i in range(5):
        try:
            response = requests.get(url)
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


def _extract_pure_func_name(func_name: str):
    # 找到第一个左括号的索引
    left_parenthesis_index = func_name.find('(')

    # 如果找到了左括号，提取括号前的部分作为纯函数名
    if left_parenthesis_index != -1:
        pure_func_name = func_name[:left_parenthesis_index]
    else:
        pure_func_name = func_name  # 如果没有括号，则返回原始字符串

    return pure_func_name


if __name__ == '__main__':
    # save_all_vulnerable_contract_txs()
    set_func_modify_state()
