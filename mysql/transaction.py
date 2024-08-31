class TransactionDB:

    def __init__(self, from_address, to_address, txhash, name, functionName, methodId, timeStamp):
        self.from_address = from_address
        self.to_address = to_address
        self.txhash = txhash
        self.name = name
        self.timeStamp = timeStamp
        self.functionName = functionName
        self.methodId = methodId
