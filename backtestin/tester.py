from datetime import datetime
from itertools import product

import backtrader as bt

class Strategy1(bt.Strategy):
    # Define your strategy logic for Strategy1 here
    pass

class Strategy2(bt.Strategy):
    # Define your strategy logic for Strategy2 here
    pass

# List of stock symbols
stocks = ['AAPL', 'MSFT', 'GOOGL']

# List of strategy classes
strategies = [Strategy1, Strategy2]

def run_backtest(strategy_class, data_feed):
    cerebro = bt.Cerebro()
    cerebro.adddata(data_feed)
    cerebro.addstrategy(strategy_class)
    cerebro.run()

def run_all_strategies(data_feed):
    for strategy_class in strategies:
        run_backtest(strategy_class, data_feed)

def run_single_strategy(strategy_class, data_feed):
    run_backtest(strategy_class, data_feed)

def run_all_stocks(strategy_class):
    for stock in stocks:
        run_backtest(strategy_class, data_feed)

def run_explore():
    for strategy_class in strategies:
        for stock in stocks:
            run_backtest(strategy_class, data_feed)

if _name_ == '_main_':
    explore = True
    allstrategy = True
    allstocks = True

    for stock in stocks:
        data_feed = bt.feeds.YahooFinanceData(dataname=stock, fromdate=datetime(2020, 1, 1), todate=datetime(2023, 1, 1))
        #data explore will be run for each data feed which does not make sense

    if explore:
        combinations = product(strategies, stocks)
        for combo in combinations:
            strategy, stock = combo[0], combo[1]
            data_feed = bt.feeds.YahooFinanceData(dataname=stock, fromdate=datetime(2020, 1, 1), todate=datetime(2023, 1, 1))
            run_backtest(strategy, data_feed)
    else:
        if allstrategy:
            if allstocks:
                run_all_strategies(data_feed)
            else:
                for strategy_class in strategies:
                    run_all_stocks(strategy_class, data_feed)
        else:
            if allstocks:
                run_single_strategy(strategies[0], data_feed)
            else:
                for stock in stocks:
                    data_feed = bt.feeds.YahooFinanceData(dataname=stock, fromdate=datetime(2020, 1, 1), todate=datetime(2023, 1, 1))
                    run_single_strategy(strategies[0], data_feed)