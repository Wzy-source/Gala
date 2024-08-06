from slither.core.variables import StateVariable, LocalVariable, Variable
from typing import List, TypeAlias, Optional, Tuple, Dict, Set
from slither.core.declarations import Function


def is_eoa_callable_func(func: Function) -> bool:
    if func.is_receive or func.is_fallback or func.is_constructor:
        return False
    return func.visibility in ["public", "external"]


def get_fun_params_in_taint_vars(tainted_vars: Set[Variable], func: Function) -> Set[Tuple[LocalVariable, int]]:
    tainted_params: Set[Tuple[LocalVariable, int]] = set()
    for pindex in range(0, len(func.parameters)):
        param = func.parameters[pindex]
        if param in tainted_vars:
            tainted_params.add((param, pindex))
    return tainted_params

