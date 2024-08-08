// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract OwnableContract {
    address public owner;
    uint256 public value;
    mapping(address => uint) public balances;

    // 构造函数，部署合约时将部署者设为owner
    constructor() {
        owner = msg.sender;
    }

    function update(uint newBalance) public {
        balances[msg.sender] = newBalance;
    }

    // onlyOwner修饰符，限制函数只能由owner调用
    modifier onlyOwner() {
        require(msg.sender == owner, "Caller is not the owner");
        _;
    }

    // changeOwner函数，允许owner将所有权转移给新地址
    function changeOwner(address newOwner) public {
        require(newOwner != address(0), "New owner is the zero address");
        owner = newOwner;
    }

    // 示例函数，只有owner可以调用
    function ownerFunction(uint256 newValue) public onlyOwner {
        // 只有owner可以执行的代码
        value = newValue;
    }
}
