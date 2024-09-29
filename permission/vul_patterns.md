# Privilege Check Points(在论文中将这些bug一一对应于所示例子)

## State Variable Modification
- 影响合约控制流
- 修改任意其他调用者的状态（arbitrary write）
- 访问数据结构的任意位置：Index指令（key）可以是任意值，适用于mapping和array

## Reinit/Self-destruct Reachable
- 未授权的自毁/重新初始化函数

## Delegatecall Misuse

## Transfer Money


Broken access control in smart contracts occurs in the following seven ways:

1. Authorization Through tx.origin

2. Unprotected Ether Withdrawal

3. Unprotected Selfdestruct Instruction

4. Delegatecall to Untrusted Callee

5. Write to Arbitrary Storage Location

6. Hash Collisions With Multiple Variable Length Arguments

7. Unencrypted Private Data On-Chain
