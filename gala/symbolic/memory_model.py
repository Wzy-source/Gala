from typing import Dict, List
from slither.core.variables import Variable, StateVariable
from slither.core.declarations import SolidityVariableComposed
from slither.slithir.operations import Operation
from slither.slithir.variables import Constant
from z3 import (ExprRef, Solver, Int, String, BitVec, Bool, BoolSort, Array, BitVecSort, ArraySort, BoolVal, BitVecVal, ArrayRef, DatatypeRef,
                Datatype, ArraySortRef)
from gala.sequence import Transaction
from slither.core.solidity_types import ElementaryType, ArrayType, MappingType, Type, UserDefinedType

from enum import Enum, auto


class MULocation(Enum):
    STORAGE = auto()
    MEMORY = auto()


class MemoryModel:
    def __init__(self, mu_location: MULocation):
        self.MU: Dict[Variable, any] = dict()
        self.location: MULocation = mu_location

    # ======================= 创建符号化变量 =======================

    def create_var(self, var: Variable):
        if isinstance(var, Constant):
            # 1.处理常量/字面量（字符串字面量/整数字面量/布尔字面量等）
            # 如果是常量，每次均新创建一个，而不是保存在MU中
            # 这是由于Constant类型实现的hash函数是仅依赖于value的，会导致相同Value的不同节点映射到一个符号值
            res_var = self.create_symbolic_constant(var)
        else:
            # 2.根据Slither变量的类型，来创建具体的符号变量
            res_var = self.create_symbolic_var(var.name, var.type)
            self.MU[var] = res_var

        return res_var

    def create_symbolic_var(self, var_name: str, var_type: Type):
        # Very Important Function
        if isinstance(var_type, ElementaryType):
            # address bool string int uint Byte
            return self.create_elementary_var(var_name, var_type)

        elif isinstance(var_type, ArrayType):
            array_sort = self.create_array_sort(var_type)
            return Array(var_name, array_sort.domain(), array_sort.range())

        elif isinstance(var_type, MappingType):
            mapping_sort = self.create_mapping_sort(var_type)
            return Array(var_name, mapping_sort.domain(), mapping_sort.range())
        # elif isinstance(var_type, UserDefinedType):
        #     struct_sort = self.create_user_defined_sort(var_type)
        #     return struct_sort(var_name)
        else:
            if isinstance(var_type, List) and len(var_type) == 1:  # 不知道为什么slither解析的type有时候是List
                return self.create_symbolic_var(var_name, var_type[0])
            # 兜底处理
            else:
                return String(var_name)

    def create_symbolic_sort(self, var_type: Type):
        if isinstance(var_type, ElementaryType):
            return self.create_elementary_sort(var_type)
        elif isinstance(var_type, ArrayType):
            return self.create_array_sort(var_type)
        elif isinstance(var_type, MappingType):
            return self.create_mapping_sort(var_type)
        elif isinstance(var_type, UserDefinedType):
            return self.create_user_defined_sort(var_type)
        else:
            raise Exception("Unexpected type for sort creation", str(var_type))

    @staticmethod
    def create_elementary_sort(var_type: ElementaryType):
        if str(var_type) == "address":
            return BitVecSort(256)
        elif str(var_type) == "bool":
            return BoolSort()
        elif str(var_type).startswith("uint") or str(var_type).startswith("int"):
            # 使用BitVec来创建有符号/无符号的整数
            return BitVecSort(256)  # 将所有的uint和int都统一看作256位的位向量，用以支持op操作
        elif str(var_type).startswith("bytes"):
            # 在Bytes的实现中已经对长度*8，代表比特位宽
            return BitVecSort(var_type.size)
        elif str(var_type) == "string":
            # 索引为256位的位向量，值为8位的字节
            # 存储的访问是通过 256 位的地址索引进行的，以太坊虚拟机将存储空间视为一个巨大的 2^256 字节的内存
            # 对应的索引也是使用 256 位的位向量来表示。
            return ArraySort(BitVecSort(256), BitVecSort(8))
        else:
            raise Exception("Unhandled Elementary Type:", str(var_type))

    def create_array_sort(self, var_type: ArrayType):
        # 获取数组元素的类型
        elem_type = var_type.type
        sym_elm_sort = self.create_symbolic_sort(elem_type)
        return ArraySort(BitVecSort(256), sym_elm_sort)

    def create_mapping_sort(self, var_type: MappingType):
        key_type = var_type.type_from
        value_type = var_type.type_to
        sym_key_sort = self.create_symbolic_sort(key_type)
        sym_value_sort = self.create_symbolic_sort(value_type)
        return ArraySort(sym_key_sort, sym_value_sort)

    def create_user_defined_sort(self, var_type: UserDefinedType):
        sym_struct_var = Datatype("struct")
        field_list = []
        for field in var_type.type.elems_ordered:
            field_name = field.name
            field_type = field.type
            sym_field_sort = self.create_symbolic_sort(field_type)
            field_list.append((field_name, sym_field_sort))
        sym_struct_var.declare('cons', *field_list)
        return sym_struct_var.create()

    @staticmethod
    def create_symbolic_constant(var: Constant) -> ExprRef:
        var_type = var.type
        var_name = var.name
        assert isinstance(var_type, ElementaryType)
        if str(var_type) == "address":
            return BitVecVal(var.value, 256)
        elif str(var_type) == "bool":
            return BoolVal(var.value)
        elif str(var_type).startswith("uint"):
            return BitVecVal(var.value, 256)
        elif str(var_type).startswith("int"):
            return BitVecVal(var.value, 256)
        elif str(var_type) == "string":
            # 对于字符串，可能需要转化为位向量数组或其它表示形式
            # 这里简单处理为返回固定的位向量值
            return Array(var_name, BitVecSort(256), BitVecSort(8))
        else:
            raise Exception("Unhandled Constant:", str(var))

    def create_elementary_var(self, var_name: str, var_type: ElementaryType) -> ExprRef:
        elementary_sort = self.create_elementary_sort(var_type)
        if str(var_type) == "address":
            return BitVec(f"addr_{var_name}", elementary_sort)
        elif str(var_type) == "bool":
            return Bool(var_name)
        elif str(var_type).startswith("uint") or str(var_type).startswith("int"):
            # 使用BitVec来创建有符号/无符号的整数
            # 对于Storage，在创建他时使用初始值0（符号Storage初始化的定义）
            # 而对于Memory中的变量（局部变量/函数参数），赋予符号值（函数参数可以是任意的，而不是0）
            return BitVec(var_name, elementary_sort)
        elif str(var_type).startswith("bytes"):
            # 在Bytes的实现中已经对长度*8，代表比特位宽
            return BitVec(var_name, elementary_sort)
        elif str(var_type) == "string":
            # 索引为256位的位向量，值为8位的字节
            # 存储的访问是通过 256 位的地址索引进行的，以太坊虚拟机将存储空间视为一个巨大的 2^256 字节的内存
            # 对应的索引也是使用 256 位的位向量来表示。
            assert isinstance(elementary_sort, ArraySortRef)
            return Array(var_name, elementary_sort.domain(), elementary_sort.range())
        else:
            raise Exception("Unhandled Elementary Type:", str(var_type))

    # ======================= 深拷贝 =======================
    def copy(self) -> "MemoryModel":
        new_memory_model = MemoryModel(self.location)
        for key in self.MU:
            new_memory_model.MU[key] = self.MU[key]
        return new_memory_model

    # # ======================= 工具函数 =======================

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
            return None

    def __contains__(self, item: Variable) -> bool:
        return item in self.MU
