import re
import json
from typing import Optional

version_pattern = re.compile(r'0.[1-9].\d{1,2}')


class Settings:
    def __init__(self, setting_path: str):
        self.setting_path = setting_path
        self.settings = self._read_settings()

    def _read_settings(self):
        with open(self.setting_path, "r") as file:
            return json.load(file)

    @property
    def contract_name(self) -> str:
        return self.settings['ContractName']

    @property
    def contract_address(self) -> str:
        return self.settings['Address']

    @property
    def contract_path(self)->str:
        return self.settings['ContractPath']
    @property
    def compiler_version(self) -> Optional[str]:
        res = version_pattern.search(self.settings['CompilerVersion'])
        if res:
            return res.group()
        else:
            raise ValueError("CompilerVersion not found in settings")
