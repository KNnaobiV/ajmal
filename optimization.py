from __future__ import (absolute_import, division, print_function,
	unicode_literals)
from itertools import product
from statistics import mean
from datetime import datetime


import backtrader as bt
import yfinance as yf
import pandas as pd
import numpy as np

from strategy import ZeroLagStrategy
from analyzers import SortinoRatio

params_list = []
period_vals = range(1, 48, 1 )
stop_loss_vals = np.linspace(0.01, 0.1, 47)
take_profit_vals = np.linspace(0.01, 0.1, 47)

params = list(product(period_vals, stop_loss_vals, take_profit_vals))


def optimization_filter(params):
	cerebro = bt.Cerebro()
	data = bt.feeds.PandasData(
		dataname=yf.download('SPY', '2015-07-06', '2021-07-01', auto_adjust=True)
	)
	cerebro.adddata(data)
	cerebro.optstrategy(
		ZeroLagStrategy, period=period_vals, 
		stop_loss=stop_loss_vals, take_profit=take_profit_vals
	)
	cerebro.addsizer(bt.sizers.FixedSize, stake=1000)
	cerebro.broker.setcash(100000)
	cerebro.broker.setcommission(0.01)
	cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
	cerebro.addanalyzer(SortinoRatio, _name="sortino")
	cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
	results=cerebro.run()
	sharpes = []
	sortinos = []
	params_list = [
		[
		result[0].params.period, result[0].params.stop_loss,
		result[0].params.take_profit,
		result[0].analyzers.sharpe.get_analysis()["sharperatio"],
		result[0].analyzers.sortino.get_analysis()["sortino_ratio"],
		result[0].analyzers.returns.get_analysis()["rnorm100"]
		] for result in results
	]
	pd.DataFrame(
		params_list, columns=[
			"period", "stop_loss", "take_profit", "sharpe", 
			"sortino", "returns"]
	).to_csv("params.csv", index=False)


if __name__ == "__main__":
	optimization_filter(params)
	filtered = list(filter(optimization_filter, params))
	cerebro = bt.Cerebro()
	cerebro.optstrategy(
		ZeroLagStrategy, period=period_vals, 
		stop_loss=stop_loss_vals, take_profit=take_profit_vals
	)
	cerebro.addsizer(bt.sizers.FixedSize, stake=1000)
	cerebro.broker.setcash(100000)
	cerebro.broker.setcommission(0.01)
	cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe_ratio")
	data = bt.feeds.PandasData(
		dataname=yf.download('SPY', '2015-07-06', '2021-07-01', auto_adjust=True)
	)
	cerebro.adddata(data)
	cerebro.run(maxcpus=1)
	print(filtered)