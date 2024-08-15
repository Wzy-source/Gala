// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract OwnableContract {
    address public owner;
    address public constant_owner;
    uint256 public value;
    mapping(address => uint) public balances;
    address[] public  candidates;
    bytes[16] public fix_bytes;
    string public  name;
    string public fix_name = "name";
    // 构造函数，部署合约时将部署者设为owner
    struct Validity {
        uint256 last;
        uint256 ts;
    }

    mapping (address => Validity) public validAfter;

    constructor() {
        owner = msg.sender;
    }

    function transfer(address _to, uint256 _amount) public returns (bool success) {
        validAfter[_to].ts = _amount;
        return true;
    }

    function update(uint newBalance,address _candidate) public onlyOwner {
        balances[msg.sender] = newBalance;
//        candidates.push(_candidate);
    }

    function add_candidate(address _candidate) public onlyOwner {
        candidates.push(_candidate);
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
//        constant_owner = 0x000000F20032b9E171844b00EA507E11960BD94b;
    }


//    function changeName() public onlyOwner {
//        name = "new_name_wzy";
//    }
}
