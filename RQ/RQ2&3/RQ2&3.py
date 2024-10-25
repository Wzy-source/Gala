import requests
from slither import Slither

from RQ.timeout import with_timeout, TimeoutException
from permission.crucial_op_explorer import CrucialOpExplorer
from permission.crucial_op_explorer_sm import CrucialOpExplorerSkipModeling
from permission.vul_checker import PermissionVulChecker
from mysql.api import DatabaseApi
from typing import List

API_KEY = "HPXNN2GP4VFJIBD4USI8QJF6MFI75HRQZT"


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


def test_one_contract(address: str, name: str):
    crucial_ops, vul_res, intend_res = PermissionVulChecker().check(name, address)
    return crucial_ops, vul_res, intend_res


contract_name_addr = [  # Vuls TP FP
    # ("0x9db3fd94a5bb1acdaef28ae483fe6b0d49746678", "URANUS"),  # 1 1 0
    # ("0xb5630e5dfd604b3b88965f2a5103bbf5e31a7340", "GTIX"),  # ❌ 1 1 1 Airdrop 可以保留 F
    # ("0xd7290307c040f4089f8650b7f7aac3cfe39cd6bd", "UEXCloudToken"),  # ❌ 1 1 1 Airdrop F
    # ("0xf55a32f0107523c14027c4a1e6177cd7291395a0", "EUXLinkToken"),  # ❌ 1 1 1 Airdrop F
    # ("0x97fe19dfab95b1709bb0994af18ba7f793e28cba", "MYSELF"),  # 1 1 0
    # ("0x97d25fc9024c689320dafbd9bbca8861ab669ccd", "Listen"),  # 1 1 0
    # ("0x013bf75820343cccc2cffda666bf4d5f7891e35c", "NEWTOKEN"),  # 1 1 0
    # ("0x04f4de2577b75853f721fa270d48490504f6fe99", "Welfarecoin"),  # 1 1 0
    # ("0x08ade307321221677e837c8150bdbd4e891daf09", "Vault"),  # 3 3 0
    # ("0x331655585e8893961f8e8e427f5f8dedf6e7f0af", "SDT_token"),  # 1 1 0
    # ("0x976c1926b162f4cebbd461a39fe5e5a695c132ae", "XiDingCoin"),  # 1 1 0
    # ("0x881f21d3e2d2d4f48d815f41bea8dbdcf0e24e50", "DepositVault"),  # 3 3 0
    # ("0x92949bd74c4d21852a3d9f7dfb841fad2833302b", "basisneuro"), # 1 1 0
    # ("0x97c103d006bd363588a98659a4d3b5cab9a29348", "BaliToken"), # 1 1 0
    # ("0x15438e22bb537a00ec51e27789919ce043cdb47b", "PointOneUSD"),  # 1 1 0
    # ("0x18429dedafbb65443edf60402294df5c01aee1da", "BuyerToken"),  # ⚠️编译错误，和SoMo一起解决
    # ("0x1bdeff9530aa31c1e43f5c6e53d59ce386aa8447", "zrankadictos"), # 1 1 0
    # ("0x21e0529ce64af51b957fd0c74af37d9cc1f6a2f7", "TDZ"),  # 1 1 0
    # ("0x290d7f8b8d7da1e92903405a74667c934ca8f086", "Wallet"),  #  3 3 0
    # ("0x3f2d17ed39876c0864d321d8a533ba8080273ede", "NoxonFund"),  # 1 1 0
    # ("0x48d537f3b6fd5310d63d65add71851d7b9db2fbc", "LUKE"), # 1 1 0
    # ("0x4eb3ce14fda3a874ecad0e9ad988258c827bae82", "DepositBank"),  # 1 1 0
    # ("0x62c14b73192c018026eab42b52a5118402634666", "CreateToken_ERC20"), # 1 1 0
    # ("0x712c290551ee48f6b3ccc318bd63989c5c37ead4", "TokenCoinExchanger"),  # 1 1 0
    # ("0x807b9487aaf00629b674bd6d02e4917453bc5939", "CrowdsaleToken"), # 1 1 0
    # ("0x84b774ac2140bb687a16817e33ad9b9909c25b73", "ANAToken"), # 1 1 0
    # ("0x90aa6fb2c2ab2c9e3fd5634c054d636c708cd5f3", "BuyerToken"),  # ⚠️编译错误，和SoMo一起解决
    # ("0x9ce63a4e69de34844e340fc541d82db9506287bc", "OpenDollar"), # 1 1 0
    # ("0x097581495f8f7b34ab4a0c8e48644117ba4393c2", "NeverEndingToken"),  # ❌ 运行超时
    # ("0x06eb5444bd13815a77d72e336e8fe7dedb801709", "TwoKrinkles"), # 1 1 0
    # ("0x197803b104641fbf6e206a425d9dc35dadc4f62f", "R"),  # 1 1 0
    # ("0x91151abe8cea8ee574b50cc01c18ce36cbba3195", "Vault"),  # 4 4 0
    # ("0x5822e54dbc2a20856a4740def71240c3e6f553ea", "Only"),  # 1 1 0 有一个误报，setSomeValue 可以规避
    # ("0x1044d3efad9a9bad4e77a1c0c86bc53636da0345", "MSRiseTokenSale"),  # 1 1 0
    # ("0x8e9f6181371013194d48bc031adf7fe179fb37e3", "Cryptbond"),  # ❌ 有一个误报 getTokens
    # ("0x952aa09109e3ce1a66d41dc806d9024a91dd5684", "Hospo"), # 运行超时
    # ("0x009c80EfF4F5d8fcA2B961ee607B00B9C64eF9F2", "STORH"), # 1 1 0
    # ("0x3F60A98202Cf7ac8be9aFC077e6c28f2638009F4", "RandomLedgerService"),  # 1 1 0
    # ("0xa11105f8e6bbc20c71d10d3218b9718c8abd7250", "MyFiToken"), # 1 1 0
    ("0xA21C9a3ae47103B1fD1DfA04766c4D00c19E1Ff6", "CryptoOscarsToken"),  # 1 1 0
    # ("0x013620bF5142f9D8487e92C1D514c38e1b086613", "Etherumble"), # 1 1 0
    # ("0x4eaF0A28BA6f524518DF13a75aC276683EFB7d3B", "HumanErrorToken"), # 1 1 0
    # ("0x5cb530f1B28dd9Ca7A7bE8092E96E184502269ac", "ERC223Token"),  # 1 1 0
    # ("0xD2C5c0D51c8D97D0Deb0A5eFA416DE90600Db62d", "ZiberCrowdsale"), # 1 1 0
    # ("0xCdCFc0f66c522Fd086A1b725ea3c0Eeb9F9e8814", "AURA"),  # 1 1 0
    # ("0xcc13fc627effd6e35d2d2706ea3c4d7396c610ea", "IDXM"), # 1 1 0
    # ("0x9924A7E3A2756Ab8B9A828485f052b6693AaA33E", "BAFCToken"), # 1 1 0
    # ("0x5ABC07D28DCC3B60a164d57e4E3981a090c5d6De", "BOMBBA") # 1 1 0
]

contract_name_addr2 = [
    # ('0x04ce99ba020bdac42fc42330da489afd6515a862', 'Newvestoriatovestox'), # getTokens
    # ('0x071a91b97d0500e0547f0289144490ca088847d2', 'ClimateChangeCoin'), # getTokens
    # ('0x07678e4c603a26e92962b6e547df99929b708baa', 'METADOLLAR'),
    # ('0x0f3c1db76e44ca31e76698daa35e0d568f934f37', 'CleanFoodCrypto'),  # getTokens
    # ('0x102e3bcc2fb6a2fe4c1c4cf09021a5638008b721', 'HitexToken'),✅
    # ('0x152a744baa167bcb72edfd12e1a30870386c0bf7', 'BitmassExToken'),✅
    # ('0x156216c63ee80183368ca8dd9f10618522918784', 'WarCoin')✅
    # ('0x1d6a8165fb01a3e792fc913da2b41da2aabfac9b', 'MobileAppCoin'), #✅ 有一个误报，但可以接受
    # ('0x23d79b8bf1b34865ebd9ea3c558724ad430599da', 'Humanity'), ✅
    # ('0x24a7de87b3bd7298bbf8966fdf170c558d69ecc4', 'METADOLLAR'),  # ❌可以解决，暂未解决，有一个误报：transferOwnership
    # ('0x2807e558a7eba8d25c3a05a0e7e9a6a437a6e6a4', 'DNSResolver'),  # ❌ 编译错误 已登记
    # ('0x2ab328ddcc578d897775f0dcc8c1ea495049031f', 'ToxbtcToken'),  # 运行超时，Z3一直卡着不动
    # ('0x2b34ebda72bade6e6e91883ca67eb23484b045fb', 'kn0Token'),  # 有两个误报：transfer和transferFrom
    # ('0x2bd1f12269c1ff80042c8d354bba4c1ca52e2061', 'STQToken'),
    # ('0x2d295c19f405048c576b4c1179ea2458e8e13935', 'x32323'), ✅
    # ('0x2fef874df01676d409163a65e5c2fc5e325f6479', 'OminiraProtocol') ✅
    # ('0x36f726e01cc85fdb0d998dfc442856379c569274', 'EthRoulette'), ✅
    # ('0x3cb8c8026557623bde4b3923c6ee0c398b85ce47', 'AchimPowh'),  # ✅有一个误报，不过可以接受
    # ('0x3da034753b42bda1bcfa682f29685e2fd6729016', 'VoipToken'),✅
    # ('0x412d99a1f370d5d750b9bdf197b0a4bee2bc4e60', 'Ethtex'),✅
    # ('0x43e6546d22166e931043c5082777725ff3ebcf00', 'ATTC'),✅
    # ('0x43efc486d1c7c5cb0193e409a73aa33786f5197c', 'Tubigo'),✅
    # ('0x50430b6201c9859c91a5590ac71700cc71499a0e', 'GetPaid'),✅
    # ('0x54e41aefc0eca9f491c7316e1c1741b2b3cce3c8', 'ToxbtcToken'),✅
    # ('0x660fcb0834b1293117d472d65186534acf75af4f', 'SecureDeposit'),✅
    # ('0x625f220be6440c14f3481072f1cbe9a83a58ec75', 'Deposit'),  # 有一个误报Deposit.setReleaseDate，已登记
    # ('0x6f5c1ed62a4fa41cfc332d81fafd3cd38aacbd85', 'Vault'),✅
    # ('0x3616f0d3d088e488c291e82a1762a7591661e639', 'XToken'), # 编译错误
    # ('0x5aef06ec39e98c05201ee1e54b653c372ecb9cf3', 'FALCON'),✅
    # ('0x5da354ebda60d93dab822b10fe0925489f0b9db7', 'chaincybercmctmovie'),✅
    # ('0x612f1bdbe93523b7f5036efa87493b76341726e3', 'HOTTO'),✅
    # ('0x78af01b310a23d25009bdfb95ef06e9a5584fb80', 'HOTTO'),✅
    # ('0x66d58f0a2a44742688843ceb8c0fa8d8567e3c54', 'DoubleOrNothingImpl'),
    # ('0x6b31a898f7e711b323a6212eac4ae250e0d6624f', 'EthLendToken'),✅
    # ('0x6f3d1879cd84fa1a7eec7fe936af6a84b67f4567', 'ERC721dAppCaps'),  # ⚠️TODO 重新审查
    # ('0x70d146a7dc622772b9d4b4fc02f28516ce237011', 'DARTTOKEN'),✅
    # ('0x724e3a236d3e9c8ad2c3d1aff181118e6e9b3026', 'BITCOINMILLIONARE'),✅
    # ('0x75e494f8a92ad1daa4fd6e78cbac33f84c2f25b9', 'LuckyNumberImp'), # ❌ 有两个误报，TODO 未解决
    # ('0x766ce08cd40b31b79b3681bce55f61e6efc4edfa', 'TokenController'),
    # ('0x76880e1ab0bf868bd7ff97264dc23880739dfbdc', 'KingOfNarnia'), # Slither编译错误
    # ('0x7dd921651b1d6e92a09b92e03769e8f6360efefd','NEXTARIUM')✅
    # ('0x9402cedd72e6e586e092caa2760887e24a8a3b5b','Fiocoin') ✅
    # ('0x68cadbcdd5a14e89364f0535fdef62f0f1b9d025','SurgeToken') ✅
    # ('0x6970bbe0df628b1e2dce874daaa529c0ceff54ff', 'XVOToken')  # 有一个误报 已经记录
    # ('0x5088b94cf8a1143eb228b6d3f008350ca742ddc2', 'EtherCartel'), # ✅
    # ('0xe7f445b93eb9cdabfe76541cc43ff8de930a58e6', 'ForceProfitSharing'),  # xForce，真实案例 有2个误报 已登记
    # ('0x860eb6f729ab3957fd5b3054d80d0b04037efdda', 'BankingPay'), # ✅
    # ('0x07678e4c603a26e92962b6e547df99929b708baa', 'METADOLLAR'),  # ✅
    # ('0x68af0f18c974a9603ec863fefcebb4ceb2589070', 'PIGGYBANK'),
    # ('0x6f3d1879cd84fa1a7eec7fe936af6a84b67f4567', 'ERC721dAppCaps'),
    # ('0x75e494f8a92ad1daa4fd6e78cbac33f84c2f25b9', 'LuckyNumberImp'),
    # ('0x766ce08cd40b31b79b3681bce55f61e6efc4edfa', 'TokenController'),
    # ('0xfa82f0a05b732deaf9ae17a945c65921c28b16dd', 'GEOPAY'),
    # ('0xfb025f588cd68b9ddd30e4c3919748e87e5c6265', 'Aeromart')
    ('0x07678e4c603a26e92962b6e547df99929b708baa', 'METADOLLAR')
    # ('0x952aa09109e3ce1a66d41dc806d9024a91dd5684', 'Hospo')
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


def fetch_contract_compiler(address):
    """
    根据智能合约地址获取验证过的合约源代码
    """
    req_url = f"https://api.etherscan.io/api?" \
              f"module=contract&" \
              f"action=getsourcecode&" \
              f"address={address}&" \
              f"apikey={API_KEY}"
    response = requests.get(req_url)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == '1':
            result = data['result'][0]
            # 如果是未验证的合约，返回的source_code和contract_name都为""
            compiler = result['CompilerVersion'].split("-")[0].replace("v", "")
            compiler = compiler.split("+")[0]
            return compiler
        else:
            print("API请求失败：", "message", data['message'], "result ", data['result'])
    else:
        print("API请求失败：", 'response.status_code ', response.status_code)


def save_compiler_version():
    db_api = DatabaseApi()
    all_contracts = db_api.get_all_verified_pev_contract()
    for contract in all_contracts:
        address = contract[0]
        compiler = fetch_contract_compiler(address)
        print(address, compiler)
        db_api.save_compiler_version_in_verified_pev(compiler, address)


def test_all_verified_contracts():
    db_api = DatabaseApi()
    all_verified_contracts = db_api.get_all_verified_pev_contract()
    for contract in all_verified_contracts:
        address = contract[0]
        name = contract[1]
        verified_res = contract[2]
        has_run = contract[13]
        if has_run:
            continue
        print(f"======================ANALYSIS {name}:{address}==========================")
        try:
            crucial_ops, vul_res, intend_res = test_one_contract(address, name)
            if verified_res == 1:
                vul_num = len(vul_res.keys())
                if vul_num == 1:
                    db_api.save_gala_verified_result(address, 1, 0, 0)
                    print(f"save {name}:{address}, vul_num:{1}")
                else:
                    print(f"has false positive:{name}:{address}")
            print()
        except Exception as e:
            if isinstance(e, TimeoutException):
                print("Time Out Error")
            print(f"Analysis Error:{name}:{address}")


def test_selected_contracts():
    db_api = DatabaseApi()
    for contract in contract_name_addr2:
        address = contract[0]
        name = contract[1]
        print(f"======================ANALYSIS {name}:{address}==========================")
        try:
            crucial_ops, vul_res, intend_res = test_one_contract(address, name)
            vul_num = len(vul_res.keys())
            if vul_num == 1:
                db_api.save_gala_verified_result(address, 1, 0, 0)
                print(f"save {name}:{address}, vul_num:{1}")
            elif vul_num == 0:
                print(f"no vul result:{name}:{address}")
            else:
                print(f"has false positive:{name}:{address}")
            print()
        except Exception as e:
            if isinstance(e, TimeoutException):
                print("Time Out Error")
            print(f"Analysis Error:{name}:{address}")
            raise e


def test_avg_op_num():
    db_api = DatabaseApi()
    all_verified_contracts = db_api.get_all_verified_pev_contract()
    all_op_num = 0
    all_contract_analyzed = 0
    for contract in all_verified_contracts:
        address = contract[0]
        name = contract[1]
        try:
            slither = Slither(target=address, etherscan_api_key=API_KEY, disable_solc_warnings=True)
            main_contract = slither.get_contract_from_name(name)
            assert len(main_contract) == 1, f"No Contract Or Multiple Contracts Named {name}"
            main_contract = main_contract[0]
            crucial_ops = CrucialOpExplorer().explore(main_contract)
            all_op_num += len(crucial_ops)
            all_contract_analyzed += 1
            print(f"all op num:{all_op_num}")
            print(f"all contract analyzed: {all_contract_analyzed}")
            print(f"average operations:{all_op_num / all_contract_analyzed}")
        except Exception as e:
            print(e)
    print(f"final op num:{all_op_num}")
    print(f"final contract analyzed: {all_contract_analyzed}")
    print(f"final average operations:{all_op_num / all_contract_analyzed}")


def test_avg_op_num_sm():
    db_api = DatabaseApi()
    all_verified_contracts = db_api.get_all_verified_pev_contract()
    all_op_num = 0
    all_contract_analyzed = 0
    for contract in all_verified_contracts:
        address = contract[0]
        name = contract[1]
        try:
            slither = Slither(target=address, etherscan_api_key=API_KEY, disable_solc_warnings=True)
            main_contract = slither.get_contract_from_name(name)
            assert len(main_contract) == 1, f"No Contract Or Multiple Contracts Named {name}"
            main_contract = main_contract[0]
            crucial_ops = CrucialOpExplorerSkipModeling().explore(main_contract)
            all_op_num += len(crucial_ops)
            all_contract_analyzed += 1
            print(f"all op num:{all_op_num}")
            print(f"all contract analyzed: {all_contract_analyzed}")
            print(f"average operations:{all_op_num / all_contract_analyzed}")
        except Exception as e:
            print(e)
    print(f"final op num:{all_op_num}")
    print(f"final contract analyzed: {all_contract_analyzed}")
    print(f"final average operations:{all_op_num / all_contract_analyzed}")


if __name__ == '__main__':
    # for addr_name in contract_name_addr2:
    #     address = addr_name[0]
    #     name = addr_name[1]
    #     test_one_contract(address, name)
    # save_compiler_version()
    # test_all_verified_contracts()
    # test_selected_contracts()
    test_avg_op_num_sm()
