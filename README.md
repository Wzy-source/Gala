# Gala

This is a repository for our paper "Gala: Automatically Generating Symbolic Transaction
Sequences for Detecting Privilege Escalation Vulnerabilities
in Smart Contracts"


## Gala Implementation Code
- `permission`: 用于基于Slither编译合约并收集critical operations
- `gala`: 基于critical operations发掘可能引发PEV的符号化交易序列

## Experiment Scripts
- `data`: 用于获取实验数据的脚本
- `RQ`: 四个Research Questions的实验代码
- `mysql`用于保存合约数据和实验结果的数据库脚本文件

