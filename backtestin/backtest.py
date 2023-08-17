import asyncio
import tracemalloc
import sys
import time
sys.path.append("..")

from collections.abc import Iterable
from itertools import product
import backtrader as bt
import pandas as pd
import yfinance as yf
from fastquant import get_stock_data
from fastquant.backtest.data_prep import initalize_data
from fastquant.backtest.post_backtest import analyze_strategies

from ajmal.strategy import ZeroLagStrategy


STRATEGY_MAPPING = {
    "rsi": "RSIStrategy",
    "smac": "SMACStrategy",
    "base": "BaseStrategy",
    "macd": "MACDStrategy",
    "emac": "EMACStrategy",
    "bbands": "BBandsStrategy",
    "buynhold": "BuyAndHoldStrategy",
    "sentiment": "SentimentStrategy",
    "custom": "CustomStrategy",
    "ternary": "TernaryStrategy",
    "buynhold": ZeroLagStrategy,
}


def get_logging_params(verbose):
    verbosity_args = dict(
        strategy_logging=False,
        transaction_logging=False,
        periodic_logging=False,
    )
    if verbose > 0:
        verbosity_args["strategy_logging"] = True
    if verbose > 1:
        verbosity_args["transaction_logging"] = True
    if verbose > 2:
        verbosity_args["periodic_logging"] = True

    return verbosity_args


# async 
def process_backtest_results(
    symbol,
    tstart,
    tend,
    init_cash,
    stratruns,
    data,
    strat_names,
    strategy,
    strategies,
    sort_by,
    return_history,
    verbose,
    multi_line_indicators,
    plot,
    return_plot,
    plot_kwargs,
    kwargs,
    cerebro,
    data_format_dict,
    figsize,
):
    if verbose > 0:
        print(f"Time used (seconds):{tend - tstart}, symbol:{symbol}")

    sorted_combined_df, optim_params, history_dict = analyze_strategies(
        init_cash,
        stratruns,
        data,\
        strat_names,
        strategy,
        strategies,
        sort_by,
        return_history,
        verbose,
        multi_line_indicators,
        **kwargs
    )
    if plot and not all_strategies:
        if sorted_combined_df.shape[0] != 1:
            if verbose > 0:
                print("===========")
                print("Plotting backtest for optimal parameters ...")
            _, fig = backtest(
                strategy,
                data,
                plot=plot,
                verbose=0,
                sort_by=sort_by,
                return_plot=return_plot,
                plot_kwargs=plot_kwargs,
                **optim_params
            )
        else:
            fig = plot_results(cerebro, data_format_dict, figsize, **plot_kwargs)
    if return_history and return_plot:
        return sorted_combined_df, history_dict, fig
    elif return_history:
        return sorted_combined_df, history_dict
    elif return_plot:
        return sorted_combined_df, fig
    else:
        return sorted_combined_df


def get_yahoo_data(symbol, start_date, end_date, dividends=True):
    df = yf.download(symbol, start=start_date, end=end_date)
    df = df.reset_index()
    df["Date"] = df["Date"].dt.tz_localize(tz="UTC")
    rename_dict = {
        "Date": "dt",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
        "Dividends": "dividend",
    }
    if dividends:
        ticker = yf.Ticker(symbol)
        div_df = ticker.dividends

        if div_df.shape[0] > 0:
            df = df.join(div_df, how="left", on="Date")
        else:
            df["dividend"] = 0
    else:
        df["Dividends"] = 0

    rename_list = [
        "dt",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "dividend",
    ]
    df = df.rename(columns=rename_dict)[rename_list].drop_duplicates()
    df["dividend"] = df["dividend"].fillna(0)
    df["dt"] = pd.to_datetime(df.dt)
    return df.set_index("dt")

def get_all_data(symbol, start_date, end_date):
    return initalize_data(
            get_yahoo_data(symbol, start_date, end_date), strategy_name=""
        )

# async 
def prep_results(
    cerebro,
    data,
    data_format_dict,
    symbols,
    strategies,
    strategy="", #include strategies
    commission=0.001,
    init_cash=100000,
    buy_prop=1,
    sell_prop=0.75,
    plot=False,
    fractional=False,
    slippage=0.001,
    single_position=None,
    verbose=1,
    sort_by="rnorm",
    sentiments=[],
    return_history=True,
    return_plot=False,
    channel="",
    allow_short=True,
    short_max=1,
    sizer=None,
    figsize=(30, 15),
    multi_line_indicators=None,
    data_class=None,
    data_kwargs={},
    plot_kwargs={},
    fig=None,
    **kwargs
    ):
    tracemalloc.start()
    #add_strategy_settings(cerebro, init_cash, kwargs)
    #add_strategy_observers(cerebro)
    #add_strategy_analyzers(cerebro)
    kwargs = {
        k: v if isinstance(v, Iterable) and not isinstance(v, str) else [v]
        for (k, v) in kwargs.items()
    }
    logging_params = get_logging_params(verbose)
    kwargs.update(logging_params)

    if verbose > 0:
        print("Starting Portfolio Value: %.2f" % cerebro.broker.getvalue())
    tstart = time.time()
    
    stratruns = [cerebro.run()]
    """with concurrent.futures.ThreadPoolExecutor() as executor:
        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(executor, cerebro.run)]
        completed, _ = await asyncio.wait(tasks)
        for task in completed:
            stratruns.extend(task.result())"""
    tend = time.time()
    
    results = process_backtest_results(
        symbols,
        tstart,
        tend,
        init_cash,
        stratruns,
        data,
        strategies,
        strategy,
        strategies,
        sort_by,
        return_history,
        verbose,
        multi_line_indicators,
        plot,
        return_plot,
        plot_kwargs,
        kwargs,
        cerebro,
        data_format_dict,
        figsize,
    )
    return results

def backtest_decisions(
    cerebro, 
    symbols, 
    strategies,
    start_date,
    end_date,
    all_stocks=False, 
    all_strategies=False,
    **kwargs
):
    if all_stocks:
        if all_strategies:
            for strategy in strategies:
                cerebro.addstrategy(strategy)
                for symbol in symbols:
                    pd_data, data, data_format_dict = get_all_data(
                        symbol, start_date, end_date
                    )
                    cerebro.adddata(pd_data)
            prep_results(
                cerebro, data, data_format_dict, 
                symbols=symbols, strategies=strategies
            )
        else:
            for symbol in symbols:
                pd_data, data, data_format_dict = get_all_data(
                    symbol, start_date, end_date
                )
                cerebro.adddata(pd_data)
            for strategy in strategies:
                cerebro.addstrategy(strategy)
                prep_results(
                    cerebro, data, data_format_dict, 
                    symbols=symbols, strategies=strategy
                )
    else:
        if all_strategies:
            for strategy in strategies:
                cerebro.add(strategy)
            for symbol in symbols:
                pd_data, data, data_format_dict = get_all_data(
                    symbol, start_date, end_date
                )
                cerebro.adddata(pd_data)
                prep_results(
                    cerebro, data, data_format_dict, 
                    symbols=symbol, strategies=strategies
                )
        else:
            #this is the same as explore
            for strategy in strategies:
                cerebro.addstrategy(STRATEGY_MAPPING[strategy])
                for symbol in symbols:
                    pd_data, data, data_format_dict = get_all_data(
                        symbol, start_date, end_date
                    )
                    cerebro.adddata(pd_data)
                    prep_results(
                        cerebro, data, data_format_dict, 
                        symbols=symbol, strategies=strategy, **kwargs
                    )


# async 
def backtest_async(
    start_date, 
    end_date,
    strategies,
    symbols,
    all_strategies=False,
    all_stocks=False,
    commission=0.001,
    init_cash=100000,
    buy_prop=1,
    sell_prop=0.75,
    plot=True,
    fractional=False,
    slippage=0.001,
    single_position=None,
    verbose=1,
    sort_by="rnorm",
    sentiments=[],
    return_history=True,
    return_plot=False,
    channel="",
    allow_short=True,
    short_max=1,
    sizer=None,
    figsize=(30, 15),
    multi_line_indicators=None,
    data_class=None,
    data_kwargs={},
    plot_kwargs={},
    fig=None,
    **kwargs
):
    cerebro = bt.Cerebro(stdstats=False, maxcpus=0, optreturn=False)
    cerebro, data, data_format_dict = backtest_decisions(
        cerebro, symbols, strategies, start_date, 
        end_date, all_stocks, all_strategies, **kwargs
    )
    return prep_results(cerebro, data, data_format_dict, symbols, strategies, **kwargs)


def backtest(start_date, end_date, strategies, symbols, **kwargs):
    params = {
        "all_stocks": False,
        "all_strategies": False,
        "commission": 0.001,
        "init_cash": 100000,
        "buy_prop": 1,
        "sell_prop": 1,
        "execution_type": "limit",
        "plot": True,
        "fractional": False,
        "slippage": 0.001,
        "single_position": None,
        "verbose": 1,
        "sort_by": "rnorm",
        "sentiments": [],
        "return_history": False,
        "return_plot": True,
        "channel": "",
        "allow_short": True,
        "short_max": 0.75,
        #"sizer": FastQuantSizer(),
        "figsize": (30, 15),
        "multi_line_indicators": None,
        "data_class": None,
        "data_kwargs": {},
        "plot_kwargs": {},
        "fig": None,
    }
    params.update(kwargs)
    #result = asyncio.run(
    result = backtest_async(start_date, end_date, strategies, symbols, **params)
    #)
    return result

backtest("2022-01-01", "2023-05-01", strategies=["buynhold"], symbols=["SPY"])
sys.stdout.write(f"{backtest}")
