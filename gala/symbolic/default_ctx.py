# 默认构造函数中的执行环境字段（部署者）由于不支持跨合约调用，默认sender和origin的值是相同的
DEFAULT_CONSTRUCTOR_CTX = {
    "msg.sender": "0x71a15ac12ee91bf7c83d08506f3a3588143898b5",
    "tx.origin": "0x71a15ac12ee91bf7c83d08506f3a3588143898b5"
}

# 默认被调用函数中的执行环境字段（攻击者）
DEFAULT_TX_CTX = {
    "msg.sender": "0xcfd06749b04cc6ec83a60ff8df7e7936385d05b0",
    "tx.origin": "0xcfd06749b04cc6ec83a60ff8df7e7936385d05b0"
}
