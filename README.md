# Gala

This is a repository for our paper "Gala: Automatically Generating Symbolic Transaction
Sequences for Detecting Privilege Escalation Vulnerabilities
in Smart Contracts"


## Gala Implementation Code
- `permission`: Used to compile contracts with Slither and collect critical operations
- `gala`: Discovers symbolic transaction sequences that may trigger privilege escalation vulnerabilities (PEVs) based on critical operations

## Experiment Scripts
- `data`: Script for obtaining experimental data
- `RQ`: Experimental code for the four Research Questions
- `mysql`: Database script file for storing contract data and experimental results
