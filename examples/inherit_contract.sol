// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
// Base contract A
contract A {
    string public name;

    constructor() public {
        name = "Contract A";
    }
}

// Base contract B
contract B {
    string public info;

    constructor() public {
        info = "Contract B";
    }
}

// Derived contract C, inheriting from A and B
contract C is A, B {
    string public details;

    constructor() public {
        details = "Contract C";
    }
}

// Derived contract D, inheriting from C
contract D is C {
    string public description;

    constructor() public {
        description = "Contract D";
    }
}
