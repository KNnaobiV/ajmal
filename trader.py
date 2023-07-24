import configparser

import backtrader as bt
from strategy import ZeroLagStrategy

cfg = configparser.ConfigParser()
cfg.read_file("trader.cfg")

HOST = cfg.get("TRADER", "HOST")
PORT = cfg.get("TRADER", "PORT")
CLIENT_ID = cfg.get("TRADER", "CLIENT_ID")
DATANAME = cfg.get("TRADER", "DATANAME")


class LiveZeroLag(ZeroLagStrategy):
    data_live = False

    def notify_data(self, data, status):
        if status == data.LIVE:
            self.data_live = True

    def next(self):
        if not self.data_live:
            return
        super().next(self)


if __name__=="__main__":
    cerebro = bt.Cerebro()
    store = bt.stores.IBStore(port=PORT)

    data = store.getdata(dataname=DATANAME, timeframe=bt.TimeFrame.Ticks)
    cerebro.broker = store.getbroker()
    cerebro.addstrategy(LiveZeroLag)
    cerebro.run()