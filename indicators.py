import backtrader as bt

class ZeroLagEMAIndicator(bt.Indicator):
	lines = ("zlema",)
	#params = (
	#	("period", 10), 
	#	("offset", 0),
	#)
	params = dict(period=10, offset=0)
	def __init__(self):
		self.params = {"period": 10, "offset": 0}
		ema = bt.indicators.EMA(period=self.params["period"])
		self.l.zlema = ema + (ema - bt.indicators.EMA(
			period=self.params["period"] - self.params["offset"])
		)