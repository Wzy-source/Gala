/**
 *Submitted for verification at Etherscan.io on 2017-10-11
*/

pragma solidity ^0.4.15;

contract Vault {


    address Owner;
    mapping(address => uint) public Deposits;
    uint minDeposit;
    bool Locked;
    uint Date;

    function Vault() payable {
        Owner = msg.sender;

    }

    modifier onlyOwner {if (msg.sender == Owner) _;}

//    function withdraw(uint amount) payable onlyOwner { withdrawTo(msg.sender, amount); }
//
    function withdrawTo(address to, uint amount) onlyOwner {
        if (WithdrawalEnabled()) {
            uint max = Deposits[msg.sender];
            if (max > 0 && amount <= max) {

                to.transfer(amount);
            }
        }
    }


    function transferOwnership() public {Owner = msg.sender;}

    function suicide() onlyOwner public {
        selfdestruct(Owner);
    }

    function SetReleaseDate(uint NewDate) onlyOwner { Date = NewDate; }
//
    function WithdrawalEnabled() internal returns (bool) { return Date > 0 && Date <= now; }
//    function lock()  { Locked = true; }
//    modifier isOpen { if (!Locked) _; }
}
