from math import sqrt

import backtrader as bt
from backtrader.mathsupport import average, standarddev
import numpy as np


class SortinoRatio(bt.Analyzer):
    def __init__(self):
        self.returns = []
        self.downside_returns = []
        self.sortino_ratio = 0.0

    def next(self):
        # calculate the return for the current period
        returns = (self.strategy.data.close[0] - self.strategy.data.close[-1]) / self.strategy.data.close[-1]
        self.returns.append(returns)

        # calculate the downside return for the current period
        downside_ret = np.maximum(0.0, -returns - rf)
        self.downside_returns.append(downside_ret)

        # calculate the Sortino Ratio
        downside_std = np.std(self.downside_returns)
        if downside_std != 0:
            self.sortino_ratio = np.mean(self.returns) / downside_std

    def get_analysis(self):
        return {"sortino_ratio": round(self.sortino_ratio, 4)}
