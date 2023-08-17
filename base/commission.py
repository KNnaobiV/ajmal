import backtrader as bt

class CustomCommission(bt.CommissionInfo):
    params = (
        ("stock", 0.01),
        ("forex", 0.002),
    )

    def getcommission(self, size, price, pseudoexec):
        if isinstance(pseudoexec, bt.CashOperation):
            if pseudoexec.data.sec_type == bt.SecType.Stock:
                return abs(size) * self.p.stock
            elif pseudoexec.data.sec_type == bt.SecType.Forex:
                return abs(size) * self.p.forex
        return 0