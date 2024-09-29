import csv
import requests
from mysql.api import DatabaseApi

# 设置Etherscan API Key
API_KEY = "HPXNN2GP4VFJIBD4USI8QJF6MFI75HRQZT"
input_file = "/Users/mac/code/Gala-2.0/data/vulnerable_contract.csv"  # 替换为你的文件名
# Etherscan API 请求URL模板
etherscan_api_url = "https://api.etherscan.io/api?module=contract&action=getsourcecode&address={}&apikey={}"


def get_contract_name(address):
    url = etherscan_api_url.format(address, API_KEY)
    response = requests.get(url)
    data = response.json()

    if data["status"] == "1" and data["message"] == "OK":
        contract_info = data["result"][0]
        contract_name = contract_info.get("ContractName", "N/A")
        return contract_name
    else:
        return "Not Found"


if __name__ == '__main__':
    db_api = DatabaseApi()
    with open(input_file, mode='r') as infile:
        reader = csv.reader(infile)
        header = next(reader)  # 跳过第一行（列名）
        # 遍历输入CSV文件中的每一行
        for row in reader:
            address = row[0]  # 假设地址在第一列
            name = get_contract_name(address)
            # 写入数据库
            db_api.save_contract_address_name(address, name)
            print(f"Processed: {address} -> {name}")
