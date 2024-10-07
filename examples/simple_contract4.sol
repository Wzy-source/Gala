/**
 *Submitted for verification at Etherscan.io on 2017-10-11
*/

pragma solidity ^0.4.15;

contract Vault {




    address Owner;
    mapping (address => uint) public Deposits;
    uint minDeposit;
    bool Locked;
    uint Date;

//    function initVault() isOpen payable {
//        Owner = msg.sender;
//        minDeposit = 0.5 ether;
//        Locked = false;
//    }


//    function withdraw(uint amount) payable onlyOwner { withdrawTo(msg.sender, amount); }
//
//    function withdrawTo(address to, uint amount) onlyOwner {
//        if (WithdrawalEnabled()) {
//            uint max = Deposits[msg.sender];
//            if (max > 0 && amount <= max) {
//
//                to.transfer(amount);
//            }
//        }
//    }

    function transferOwnership(address to) onlyOwner { Owner = to; }


//    function SetReleaseDate(uint NewDate) { Date = NewDate; }
//
//    function WithdrawalEnabled() internal returns (bool) { return Date > 0 && Date <= now; }
//    function lock() { Locked = true; }
    modifier onlyOwner { if (msg.sender == Owner) _; }
//    modifier isOpen { if (!Locked) _; }
}
