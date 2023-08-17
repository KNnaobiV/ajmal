import backtrader as bt
from ajmal.indicators import ZeroLagEMAIndicator

from ajmal.query_api import get_yfinance_data as get_yf_data

class ZeroLagStrategy(bt.Strategy):
	params = (
		("period", 20),
		("offset", 0),
		("stop_loss", 0.02),
		("take_profit", 0.01),
	)
	def log(self, txt, dt=None):
		dt = dt or self.datas[0].datetime.date(0)
		print(f"{dt.isoformat()} {txt} ") #comment for optimization

	def __init__(self):
		self.order = None
		self.zlema = ZeroLagEMAIndicator(
			period=self.params.period, 
			offset=self.params.offset,
		)
		self.buy_signal = bt.indicators.CrossOver(self.data.close, self.zlema)
		self.sell_signal = bt.indicators.CrossDown(self.data.close, self.zlema)


	def notify_order(self, order):
		if order.status in [order.Submitted, order.Accepted]:
			return
		if order.status in [order.Completed]:
			if order.isbuy():
				self.log(
					f"BUY @ Price: {order.executed.price:.2f}, "
					f"Cost: {order.executed.value:2f}, "
					f"Comm: {order.executed.comm:.2f}"
					)
			elif order.issell():
				self.log(
					f"SELL @ Price: {order.executed.price:.2f} "
					f"Cost: {order.executed.value:2f}, "
					f"Comm: {order.executed.comm:.2f}"
					)
		elif order.status in [order.Canceled, order.Margin, order.Rejected]:
			self.log("Order Canceled/Margin/Rejected")

		self.order = None


	def notify_trade(self, trade):
		if not trade.isclosed:
			return

		self.log(
			f"OPERATION PROFIT: \n GROSS {trade.pnl:.2f}, "
			f"NET {trade.pnlcomm:.2f}"
			)


	def next(self):
		if self.order:
			return

		if self.position:
			if (self.data.close 
				>= (1 + self.params.take_profit) * self.position.price):
				self.order = self.sell()
			elif (self.data.close 
				<= (1 - self.params.stop_loss) * self.position.price):
				self.order = self.buy()

		else:
			if self.buy_signal > 0:
				self.order = self.buy()
			elif self.sell_signal > 0:
				self.order = self.sell()


if __name__=="__main__":
	cerebro = bt.Cerebro()
	cerebro.addstrategy(ZeroLagStrategy)
	get_yf_data()
	data = bt.feeds.YahooFinanceCSVData(
		dataname="temp.csv",
	)
	
	cerebro.adddata(data)
	#cerebro.resampledata(query_data, bt.TimeFrame.Minutes, compression=60)
	cerebro.broker.setcash(100000)
	cerebro.broker.setcommission(commission=0.01)
	cerebro.run()
	print(f"Portfolio end value = {cerebro.broker.getvalue()}")
	#cerebro.plot()