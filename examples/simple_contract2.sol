// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract OwnableContract {
    address public owner;
    string public name;
    uint public age;
    uint public year;


    constructor() {}

    // changeOwner函数，允许owner将所有权转移给新地址
    function changeOwner() public {
        require(owner == address(0));
        owner = msg.sender;
    }


    function changeName() public {
        require(msg.sender==owner);
        name = "new_name_wzy";
        age = 13;
        require(age == 13);
        year = 2024;


    }
}
