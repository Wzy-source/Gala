from abc import ABC, abstractmethod
from typing import TypeAlias, Union, Tuple, Optional, Dict, List
from slither.core.cfg.node import Node as SlitherNode
from slither.core.declarations import Function


class Point(ABC):
    def __init__(self) -> None:
        self._fathers: List = list()
        self._sons: List = list()
        self._son_true: Optional[SlitherNode] = None
        self._son_false: Optional[SlitherNode] = None

    @abstractmethod
    def __str__(self) -> str:
        pass

    @abstractmethod
    def __hash__(self) -> int:
        pass

    @property
    def irs_ssa(self) -> None:
        return None

    @property
    def fathers(self) -> List:
        return self._fathers

    @property
    def sons(self) -> List:
        return self._sons

    @property
    def son_true(self) -> Optional[SlitherNode]:
        return self._son_true

    @son_true.setter
    def son_true(self, son):
        self._son_true = son

    @property
    def son_false(self) -> Optional[SlitherNode]:
        return self._son_false

    @son_false.setter
    def son_false(self, son):
        self._son_false = son


class EntryPoint(Point):
    def __init__(self, function: Function) -> None:
        # the function name is the full function name from the slither.
        # to prevent duplicate entry point, the function signature could be okay.
        super(EntryPoint, self).__init__()
        self.function: Function = function

    def __str__(self) -> str:
        return f"Entry Point: {self.function_name}"

    def __hash__(self) -> int:
        return hash(self.__str__)

    @property
    def function_name(self) -> str:
        return self.function.name


class ExitPoint(Point):
    def __init__(self, function: Function) -> None:
        super(ExitPoint, self).__init__()
        self.function: Function = function

    def __str__(self) -> str:
        return f"Exit Point: {self.function_name}"

    def __hash__(self) -> int:
        return hash(self.__str__)

    @property
    def function_name(self) -> str:
        return self.function.name
