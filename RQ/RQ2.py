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


# @with_timeout(60)
def test_one_contract(address: str, name: str):
    PermissionVulChecker().check(name, address)


contract_name_addr = [  # Vuls TP FP
    # ("0x9db3fd94a5bb1acdaef28ae483fe6b0d49746678", "URANUS"),  # 1 1 0
    # ("0xb5630e5dfd604b3b88965f2a5103bbf5e31a7340", "GTIX"),  # ❌ 1 1 1 Airdrop
    # ("0xd7290307c040f4089f8650b7f7aac3cfe39cd6bd", "UEXCloudToken"),  # ❌ 1 1 1 Airdrop
    # ("0xf55a32f0107523c14027c4a1e6177cd7291395a0", "EUXLinkToken"),  # ❌ 1 1 1 Airdrop
    # ("0x97fe19dfab95b1709bb0994af18ba7f793e28cba", "MYSELF"),  # 1 1 0
    # ("0x97d25fc9024c689320dafbd9bbca8861ab669ccd", "Listen"),  # 1 1 0
    # ("0x013bf75820343cccc2cffda666bf4d5f7891e35c", "NEWTOKEN"),  # 1 1 0
    # ("0x04f4de2577b75853f721fa270d48490504f6fe99", "Welfarecoin"),  # 1 1 0
    # ("0x08ade307321221677e837c8150bdbd4e891daf09", "Vault"),  # 3 3 0
    # ("0x331655585e8893961f8e8e427f5f8dedf6e7f0af", "SDT_token"),  # 1 1 0
    # ("0x976c1926b162f4cebbd461a39fe5e5a695c132ae", "XiDingCoin"),  # 1 1 0
    # ("0x881f21d3e2d2d4f48d815f41bea8dbdcf0e24e50", "DepositVault"),  # ❌3 2 1 transfer
    # ("0x92949bd74c4d21852a3d9f7dfb841fad2833302b", "basisneuro"), # 1 1 0
    # ("0x97c103d006bd363588a98659a4d3b5cab9a29348", "BaliToken"), # 1 1 0
    # ("0x15438e22bb537a00ec51e27789919ce043cdb47b", "PointOneUSD"),  # 1 1 0
    # ("0x18429dedafbb65443edf60402294df5c01aee1da", "BuyerToken"),  # ❌编译错误，和SoMo一起解决
    # ("0x1bdeff9530aa31c1e43f5c6e53d59ce386aa8447", "zrankadictos"), # 1 1 0
    # ("0x21e0529ce64af51b957fd0c74af37d9cc1f6a2f7", "TDZ"),  # 1 1 0
    # ("0x290d7f8b8d7da1e92903405a74667c934ca8f086", "Wallet"),  # ❌ 3 2 1 transfer
    # ("0x3f2d17ed39876c0864d321d8a533ba8080273ede", "NoxonFund"),  # 1 1 0
    # ("0x48d537f3b6fd5310d63d65add71851d7b9db2fbc", "LUKE"), # 1 1 0
    # ("0x4eb3ce14fda3a874ecad0e9ad988258c827bae82", "DepositBank"),  # ❌ 1 0 0 有一个漏报：对于基本类型的finalized变量是有默认值的，没有生成对应的交易序列
    # ("0x62c14b73192c018026eab42b52a5118402634666", "CreateToken_ERC20"), # 1 1 0
    # ("0x712c290551ee48f6b3ccc318bd63989c5c37ead4", "TokenCoinExchanger"),  # 1 1 0
    # ("0x807b9487aaf00629b674bd6d02e4917453bc5939", "CrowdsaleToken"), # 1 1 0
    # ("0x84b774ac2140bb687a16817e33ad9b9909c25b73", "ANAToken"), # 1 1 0
    ("0x90aa6fb2c2ab2c9e3fd5634c054d636c708cd5f3", "BuyerToken"),  # ❌编译错误，和SoMo一起解决
    # ("0x9ce63a4e69de34844e340fc541d82db9506287bc", "OpenDollar"), # 1 1 0
    # ("0x097581495f8f7b34ab4a0c8e48644117ba4393c2", "NeverEndingToken"),  # ❌ 运行超时
    # ("0x06eb5444bd13815a77d72e336e8fe7dedb801709", "TwoKrinkles"), # 1 1 0
    # ("0x197803b104641fbf6e206a425d9dc35dadc4f62f", "R"),  # 1 1 0
    # ("0x91151abe8cea8ee574b50cc01c18ce36cbba3195", "Vault"),  # 4 4 0
    # ("0x5822e54dbc2a20856a4740def71240c3e6f553ea", "Only"), # ❌ 有一个误报，setSomeValue
    # ("0x1044d3efad9a9bad4e77a1c0c86bc53636da0345", "MSRiseTokenSale"),  # 1 1 0
    # ("0x8e9f6181371013194d48bc031adf7fe179fb37e3", "Cryptbond"),  # ❌ 有一个误报 getTokens
    # ("0x952aa09109e3ce1a66d41dc806d9024a91dd5684", "Hospo"), # 运行超时
    # ("0x009c80EfF4F5d8fcA2B961ee607B00B9C64eF9F2", "STORH"), # 1 1 0
    # ("0x3F60A98202Cf7ac8be9aFC077e6c28f2638009F4", "RandomLedgerService"),  # 1 1 0
    # ("0xa11105f8e6bbc20c71d10d3218b9718c8abd7250", "MyFiToken"), # 1 1 0
    # ("0xf2baec4108306dc87e117d98912d5adac4f15ed9", "InfiniteGold"), # 1 1 0
    # ("0xA21C9a3ae47103B1fD1DfA04766c4D00c19E1Ff6", "CryptoOscarsToken"), # 1 1 0
    # ("0x013620bF5142f9D8487e92C1D514c38e1b086613", "Etherumble"), # 1 1 0
    # ("0x4eaF0A28BA6f524518DF13a75aC276683EFB7d3B", "HumanErrorToken"), # 1 1 0
    # ("0x5cb530f1B28dd9Ca7A7bE8092E96E184502269ac", "ERC223Token"),  # 1 1 0
    # ("0xD2C5c0D51c8D97D0Deb0A5eFA416DE90600Db62d", "ZiberCrowdsale"), # 1 1 0
    # ("0xCdCFc0f66c522Fd086A1b725ea3c0Eeb9F9e8814", "AURA"),  # 1 1 0
    # ("0xcc13fc627effd6e35d2d2706ea3c4d7396c610ea", "IDXM"), # 1 1 0
    # ("0x9924A7E3A2756Ab8B9A828485f052b6693AaA33E", "BAFCToken"), # 1 1 0
    # ("0x5ABC07D28DCC3B60a164d57e4E3981a090c5d6De", "BOMBBA") # 1 1 0
]


def test_contracts():
    for address_name in contract_name_addr:
        address = address_name[0]
        name = address_name[1]
        try:
            print(f"======================ANALYSIS {name}==========================")
            test_one_contract(address, name)
            print()
        except Exception as e:
            if isinstance(e, TimeoutException):
                print("Time Out Error")
            print(f"Analysis Error:{name}:{address}")
            raise e


if __name__ == '__main__':
    test_contracts()
    # addr = "0x18429dedafbb65443edf60402294df5c01aee1da"
    # name = "BuyerToken"
    # test_one_contract(addr, name)
