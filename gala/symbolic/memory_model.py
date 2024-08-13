from typing import Dict, List
from slither.core.variables import Variable, StateVariable
from slither.core.declarations import SolidityVariableComposed
from slither.slithir.operations import Operation
from slither.slithir.variables import Constant
from z3 import ExprRef, Solver, Int, String, BitVec, Bool, Array, BitVecSort, ArraySort, BoolVal, BitVecVal
from gala.sequence import Transaction
from slither.core.solidity_types import ElementaryType, ArrayType, MappingType, Type

from enum import Enum, auto


class MULocation(Enum):
    STORAGE = auto()
    MEMORY = auto()


class MemoryModel:
    def __init__(self, mu_location: MULocation):
        self.MU: Dict[Variable, any] = dict()
        self.location: MULocation = mu_location

    def alloc_symbolic_var(self, var: Variable):
        # Very Important Function
        # TODO 对于每一种检查不到的情况做兜底处理
        # 1.TODO 处理Solidity Variable
        var_type = var.type
        var_name = var.name
        if isinstance(var, SolidityVariableComposed):
            pass

        # 2.处理常量/字面量（字符串字面量/整数字面量/布尔字面量等）
        elif isinstance(var, Constant):
            assert isinstance(var_type, ElementaryType)
            if str(var_type) == "address":
                return BitVecVal(var.value, 160)
            elif str(var_type) == "bool":
                return BoolVal(var.value)
            elif str(var_type).startswith("uint"):
                return BitVecVal(var.value, var_type.size)
            elif str(var_type).startswith("int"):
                return BitVecVal(var.value, var_type.size)
            elif str(var_type) == "string":
                # 对于字符串，可能需要转化为位向量数组或其它表示形式
                # 这里简单处理为返回固定的位向量值
                return Array(var_name, BitVecSort(256), BitVecSort(8))
            else:
                print("Unhandled Constant:", str(var))

        # 3.根据Slither变量的类型，来创建具体的符号变量
        else:
            if isinstance(var_type, ElementaryType):
                # address bool string int uint Byte
                if str(var_type) == "address":
                    return BitVec(var_name, 160)
                elif str(var_type) == "bool":
                    return Bool(var_name)
                elif str(var_type).startswith("uint"):
                    # 使用BitVec来创建有符号/无符号的整数
                    return BitVec(var_name, var_type.size)
                elif str(var_type).startswith("int"):
                    return BitVec(var_name, var_type.size)
                elif str(var_type).startswith("bytes"):
                    # 在Bytes的实现中已经对长度*8，代表比特位宽
                    return BitVec(var_name, var_type.size)
                elif str(var_type) == "string":
                    # 索引为256位的位向量，值为8位的字节
                    # 存储的访问是通过 256 位的地址索引进行的，以太坊虚拟机将存储空间视为一个巨大的 2^256 字节的内存
                    # 对应的索引也是使用 256 位的位向量来表示。3
                    return Array(var_name, BitVecSort(256), BitVecSort(8))
                else:
                    print("Unhandled Elementary Type:", str(var_type))

            elif isinstance(var_type, ArrayType):
                # 数组的元素类型
                elem_type = var_type.type
                # 目前只支持数组元素是基本类型
                if isinstance(elem_type, ElementaryType):
                    # 获取数组元素的长度
                    if self.is_sizeable_elementary_type(elem_type):
                        elem_sort = BitVecSort(elem_type.size)
                        return Array(var_name, BitVecSort(256), elem_sort)
                    elif str(elem_type) == "string":
                        return Array(var_name, BitVecSort(256), ArraySort(BitVecSort(256), BitVecSort(8)))

            elif isinstance(var_type, MappingType):
                key_type = var_type.type_from
                value_type = var_type.type_to
                # 处理键类型
                if isinstance(key_type, ElementaryType) and isinstance(value_type, ElementaryType):
                    if self.is_sizeable_elementary_type(key_type):
                        key_sort = BitVecSort(key_type.size)
                        if self.is_sizeable_elementary_type(value_type):
                            return Array(var_name, key_sort, BitVecSort(value_type.size))
                        elif str(value_type) == "string":
                            return Array(var_name, key_sort, Array(var_name, BitVecSort(256), BitVecSort(8)))
                else:
                    print("Unhandled key/value type in mapping:", str(key_type), str(value_type))
                    return None

            else:
                print("Unhandled variable type:", str(var_type))

    @staticmethod
    def is_sizeable_elementary_type(elem_type: ElementaryType) -> bool:
        if str(elem_type) == "address":
            return True
        elif str(elem_type) == "bool":
            return True
        elif str(elem_type).startswith("uint"):
            return True
        elif str(elem_type).startswith("int"):
            return True
        return False

    def __setitem__(self, key: Variable, value: ExprRef):
        self.MU[key] = value

    def __getitem__(self, key: Variable):
        if key in self.MU.keys():
            return self.MU[key]
        else:
            res_var = self.alloc_symbolic_var(key)
            if res_var is not None:
                self.MU[key] = res_var
            return res_var

    def __contains__(self, item: Variable) -> bool:
        return item in self.MU
