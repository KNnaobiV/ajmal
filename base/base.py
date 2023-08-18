import yfinance as yf
import backtrader as bt
import pandas as pd

class BaseStrategy(bt.Strategy):
    params = (
        ("init_cash", 0),
        ("buy_prop", 1),
        ("sell_prop", 1),
        ("fractional", False),
        ("slippage", 0.001),
        ("single_position", None),
        ("commission", 0.001),
        ("stop_loss", 0),
        ("stop_trail", 0),
        ("take_profit", 0),
        ("execution_type", "close"),
        ("periodic_logging", False),
        ("transaction_logging", True),
        ("strategy_logging", True),
        ("channel", ""),
        ("symbol", ""),
        ("allow_short", False),
        ("short_max", 1.5),
        ("add_cash_amount", 0),
        ("add_cash_freq", "M"),
        ("invest_div", True),
    )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f'{dt.isoformat()}, {txt}')

    def update_order_history(self, order):
        self.order_history['dt'].append(self.datas[0].datetime.datetime(0))
        self.order_history['type'].append('buy' if order.isbuy() else 'sell')
        self.order_history['price'].append(order.executed.price)
        self.order_history['size'].append(order.executed.size)
        self.order_history['order_value'].append(order.executed.value)
        self.order_history['portfolio_value'].append(self.broker.getvalue())
        self.order_history['commission'].append(order.executed.comm)
        self.order_history['pnl'].append(order.executed.pnl)

    def update_periodic_history(self):
        self.periodic_history['dt'].append(self.datas[0].datetime.datetime(0))
        self.periodic_history['portfolio_value'].append(self.broker.getvalue())
        self.periodic_history['cash'].append(self.broker.getcash())
        self.periodic_history['size'].append(self.position.size)

    def __init__(self, params=None):
        if params: # to update parameters in subclasses, 
        #call super and pass new params dict
            for param_name, param_value in params.items():
                setattr(self.params, param_name, param_value)

        self.init_cash = self.params.init_cash
        self.buy_prop = self.params.buy_prop
        self.sell_prop = self.params.sell_prop
        self.execution_type = self.params.execution_type
        self.periodic_logging = self.params.periodic_logging
        self.transaction_logging = self.params.transaction_logging
        self.strategy_logging = self.params.strategy_logging
        self.fractional = self.params.fractional
        self.slippage = self.params.slippage
        self.single_position = self.params.single_position
        self.commission = self.params.commission
        self.channel = self.params.channel
        self.stop_loss = self.params.stop_loss
        self.stop_trail = self.params.stop_trail
        self.take_profit = self.params.take_profit
        self.allow_short = self.params.allow_short
        self.short_max = self.params.short_max
        self.invest_div = self.params.invest_div
        self.broker.set_coc(True)
        add_cash_freq = self.params.add_cash_freq

        if self.single_position is not None:
            self.strategy_position = -1
        else:
            self.strategy_position = None

        if add_cash_freq == 'M':
            self.add_cash_freq = '0 0 1 * *'
        elif add_cash_freq == 'W':
            self.add_cash_freq = '0 0 * * 1'
        else:
            self.add_cash_freq = add_cash_freq

        self.add_cash_amount = self.params.add_cash_amount
        self.total_cash_added = 0

        if self.strategy_logging:
            self.log('===Global level arguments===')
            self.log(f'init_cash: {self.init_cash}')
            self.log(f'buy_prop: {self.buy_prop}')
            self.log(f'sell_prop: {self.sell_prop}')
            self.log(f'commission: {self.commission}')
            self.log(f'stop_loss: {self.stop_loss}')
            self.log(f'stop_trail: {self.stop_trail}')
            self.log(f'take_profit: {self.take_profit}')
            self.log(f'allow_short: {self.allow_short}')

        self.order_history = {
            'dt': [],
            'type': [],
            'price': [],
            'size': [],
            'order_value': [],
            'portfolio_value': [],
            'commission': [],
            'pnl': []
        }
        
        self.periodic_history = {
            'dt': [],
            'portfolio_value': [],
            'cash': [],
            'size': []
        }

        self.order_history_df = None
        self.periodic_history_df = None
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datadiv = None

        if hasattr(self.datas[0], 'dividend'):
            self.datadiv = self.datas[0].dividend

        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.len_data = len(list(self.datas[0]))
        self.action = None
        self.price_bought = 0
        self.stoploss_order = None
        self.stoploss_trail_order = None

    def buy_signal(self):
        return False

    def sell_signal(self):
        return False

    def take_profit_signal(self):
        return False

    def exit_long_signal(self):
        return self.sell_signal()

    def exit_short_signal(self):
        return self.buy_signal()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            self.update_order_history(order)
            if order.isbuy():
                self.action = 'buy'
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.action = 'sell'
            
            self.bar_executed = len(self)

            if self.transaction_logging:
                self.log(f'{self.action.upper()} EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}, Size: {order.executed.size:.2f}')
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.transaction_logging:
                if not self.periodic_logging:
                    self.log(f'Cash {self.cash} Value {self.value}')
                self.log('Order Canceled/Margin/Rejected')
                self.log(f'Canceled: {order.status == order.Canceled}')
                self.log(f'Margin: {order.status == order.Margin}')
                self.log(f'Rejected: {order.status == order.Rejected}')
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        if self.transaction_logging:
            self.log(f'OPERATION PROFIT, GROSS: {trade.pnl:.2f}, NET: {trade.pnlcomm:.2f}')

    def notify_cashvalue(self, cash, value):
        if self.periodic_logging:
            self.log(f'Cash {cash} Value {value}')
        self.cash = cash
        self.value = value

    def stop(self):
        self.final_value = self.broker.getvalue()
        self.pnl = round(self.final_value - self.init_cash - self.total_cash_added, 2)

        if self.strategy_logging:
            self.log(f'Final Portfolio Value: {self.final_value}')
            self.log(f'Final PnL: {self.pnl}')
        
        self.order_history_df = pd.DataFrame(self.order_history)
        self.periodic_history_df = pd.DataFrame(self.periodic_history)
        last_date = str(self.datas[0].datetime.date(0))
        
        if self.channel:
            trigger_bot(self.symbol, self.action, last_date)

    def start(self):
        self.first_timepoint = True

    def next(self):
        if self.invest_div and self.datadiv is not None:
            self.broker.add_cash(self.datadiv)
        
        if self.add_cash_amount:
            if self.first_timepoint:
                start_date = self.datas[0].datetime.datetime(0)
                self.cron = croniter.croniter(self.add_cash_freq, start_date)
                self.next_cash_datetime = self.cron.get_next(datetime.datetime)
                
                if self.transaction_logging:
                    self.log(f'Start date: {start_date.strftime("%Y-%m-%d")}')
                    self.log(f'Next cash date: {self.next_cash_datetime.strftime("%Y-%m-%d")}')
                
                self.first_timepoint = False
            
            if self.datas[0].datetime.datetime(0) >= self.next_cash_datetime:
                self.broker.add_cash(self.add_cash_amount)
                self.next_cash_datetime = self.cron.get_next(datetime.datetime)
                self.total_cash_added += self.add_cash_amount
                
                if self.transaction_logging:
                    self.log(f'Cash added: {self.add_cash_amount}')
                    self.log(f'Total cash added: {self.total_cash_added}')
                    self.log(f'Next cash date: {self.next_cash_datetime.strftime("%Y-%m-%d")}')
        
        self.update_periodic_history()
        
        if self.periodic_logging:
            self.log(f'Close, {self.dataclose[0]:.2f}')
        
        if self.order:
            return
        
        if self.periodic_logging:
            self.log(f'CURRENT POSITION SIZE: {self.position.size}')
        
        if len(self) + 1 >= self.len_data:
            return
        
        stock_value = self.value - self.cash
        
        if self.buy_signal() and self.strategy_position in [0, -1, None]:
            self.strategy_position = 1 if self.strategy_position in [0, -1] else None
            
            if (self.fractional and self.cash >= 10) or (not self.fractional and self.cash >= self.dataclose[0]):
                if self.transaction_logging:
                    self.log(f'BUY CREATE, {self.dataclose[0]:.2f}')
                
                afforded_size = self.cash / (self.dataclose[0] * (1 + self.slippage) * (1 + self.commission))
                position_size = abs(self.position.size)
                buy_prop_size = position_size + (afforded_size - position_size) * self.buy_prop
                self.price_bought = self.data.close[0]
                
                if self.execution_type == 'close':
                    final_size = min(buy_prop_size, afforded_size)
                    
                    if not self.fractional:
                        final_size = int(final_size)
                    
                    if self.transaction_logging:
                        self.log(f'Cash: {round(self.cash, 2)}')
                        self.log(f'Price: {round(self.dataclose[0], 2)}')
                        self.log(f'Buy prop size: {round(buy_prop_size, 2)}')
                        self.log(f'Afforded size: {round(afforded_size, 2)}')
                        self.log(f'Final size: {round(final_size, 2)}')
                    
                    self.order = self.buy(size=final_size)
                    
                    if self.stop_loss:
                        stop_price = self.data.close[0] * (1.0 - self.stop_loss)
                        
                        if self.transaction_logging:
                            self.log(f'Stop price: {stop_price}')
                        
                        self.stoploss_order = self.sell(exectype=bt.Order.Stop, price=stop_price, size=final_size)
                    
                    if self.stop_trail:
                        if self.stoploss_trail_order is None:
                            if self.transaction_logging:
                                self.log(f'Stop trail: {self.stop_trail}')
                            
                            self.stoploss_trail_order = self.sell(exectype=bt.Order.StopTrail, trailpercent=self.stop_trail, size=final_size)
                        else:
                            self.cancel(self.stoploss_trail_order)
                else:
                    afforded_size = int(self.cash / (self.dataopen[1] * (1 + self.commission + 0.001)))
                    buy_prop_size = position_size + (afforded_size - position_size) * self.buy_prop
                    final_size = min(buy_prop_size, afforded_size)
                    
                    if self.transaction_logging:
                        self.log(f'Buy prop size: {round(buy_prop_size, 2)}')
                        self.log(f'Afforded size: {round(afforded_size, 2)}')
                        self.log(f'Final size: {round(final_size, 2)}')
                    
                    self.order = self.buy(size=final_size)
                    
                    if self.stop_loss:
                        stop_price = self.data.close[0] * (1.0 - self.stop_loss)
                        
                        if self.transaction_logging:
                            self.log(f'Stop price: {stop_price}')
                        
                        self.stoploss_order = self.sell(exectype=bt.Order.Stop, price=stop_price, size=final_size)
                    
                    if self.stop_trail:
                        if self.transaction_logging:
                            self.log(f'Stop trail: {self.stop_trail}')
                        
                        self.stoploss_trail_order = self.sell(exectype=bt.Order.StopTrail, trailpercent=self.stop_trail, size=final_size)
        
        elif self.sell_signal() and self.strategy_position in [1, -1, None]:
            self.strategy_position = 0 if self.strategy_position in [1, -1] else None
            
            if self.allow_short:
                if self.execution_type == 'close':
                    max_position_size = max(
                        int(self.broker.getvalue() * self.short_max * self.sell_prop / self.dataclose[1]) + self.position.size, 0)
                    
                    if max_position_size > 0:
                        if self.transaction_logging:
                            self.log(f'SELL CREATE, {self.dataclose[1]:.2f}')
                        
                        self.order = self.sell(size=max_position_size)
                else:
                    max_position_size = max(
                        int(self.broker.getvalue() * self.short_max * self.sell_prop / self.dataopen[1]) + self.position.size, 0)
                    
                    if max_position_size > 0:
                        if self.transaction_logging:
                            self.log(f'SELL CREATE, {self.dataopen[1]:.2f}')
                        
                        self.order = self.sell(size=max_position_size)
            elif stock_value > 0:
                if self.transaction_logging:
                    self.log(f'SELL CREATE, {self.dataclose[1]:.2f}')
                
                if self.execution_type == 'close':
                    if self.sell_prop == 1:
                        self.order = self.sell(size=self.position.size)
                    else:
                        self.order = self.sell(size=int(stock_value / self.dataclose[1] * self.sell_prop))
                else:
                    self.order = self.sell(size=int(self.init_cash / self.dataopen[1] * self.sell_prop))
            
            if self.stoploss_order:
                self.cancel(self.stoploss_order)
            
            if self.stoploss_trail_order:
                self.cancel(self.stoploss_trail_order)
        
        elif self.take_profit_signal():
            price_limit = self.price_bought * (1 + self.take_profit)
            
            if self.take_profit and self.position.size > 0:
                if self.data.close[0] >= price_limit:
                    if self.strategy_position is None:
                        self.strategy_position = -1
                    
                    self.sell(exectype=bt.Order.Close, price=price_limit, size=self.position.size)
        
        elif self.exit_long_signal():
            if self.position.size > 0:
                if self.strategy_position is None:
                    self.strategy_position = -1
                
                self.order = self.sell(size=self.position.size)
        
        elif self.exit_short_signal():
            if self.position.size < 0:
                if self.strategy_position is None:
                    self.strategy_position = -1
                
                self.order = self.buy(size=self.position.size)
        else:
            self.action = 'neutral'


class RSIStrategy(BaseStrategy):
    params=('rsi_period',14),('rsi_upper',70),('rsi_lower',30)
    def __init__(self, params=None):
        super().__init__(params);self.rsi_period=self.params.rsi_period;self.rsi_upper=self.params.rsi_upper;self.rsi_lower=self.params.rsi_lower
        if self.strategy_logging:print('===Strategy level arguments===');print('rsi_period :',self.rsi_period);print('rsi_upper :',self.rsi_upper);print('rsi_lower :',self.rsi_lower)
        self.rsi=bt.indicators.RelativeStrengthIndex(period=self.rsi_period,upperband=self.rsi_upper,lowerband=self.rsi_lower)
    def buy_signal(self):return self.rsi[0]<self.rsi_lower
    def sell_signal(self):return self.rsi[0]>self.rsi_upper

class MACDStrategy(BaseStrategy):
    params=('fast_period',12),('slow_period',26),('signal_period',9),('sma_period',30),('dir_period',10)
    def __init__(self):
        super().__init__();self.fast_period=self.params.fast_period;self.slow_period=self.params.slow_period;self.signal_period=self.params.signal_period;self.sma_period=self.params.sma_period;self.dir_period=self.params.dir_period
        if self.strategy_logging:print('===Strategy level arguments===');print('fast_period :',self.fast_period);print('slow_period :',self.slow_period);print('signal_period :',self.signal_period);print('sma_period :',self.sma_period);print('dir_period :',self.dir_period)
        macd_ind=bt.ind.MACD(period_me1=self.fast_period,period_me2=self.slow_period,period_signal=self.signal_period);self.macd=macd_ind.macd;self.signal=macd_ind.signal;self.crossover=bt.ind.CrossOver(self.macd,self.signal);self.sma=bt.indicators.SMA(period=self.sma_period);self.smadir=self.sma-self.sma(-self.dir_period)
    def buy_signal(self):return self.crossover>0 and self.smadir<.0
    def sell_signal(self):return self.crossover<0 and self.smadir>.0

#STRATEGY_MAPPING={'buynhold':BuyAndHoldStrategy,'rsi':RSIStrategy,'macd':MACDStrategy}

def backtest(params):
    cerebro=bt.Cerebro(stdstats=False,maxcpus=0,optreturn=False);
    def add_strategy_analyzers(cerebro):cerebro.addanalyzer(bt.analyzers.Returns, _name="returns");
    def add_strategy_observers(cerebro):cerebro.addobserver(bt.observers.BuySell);
    add_strategy_observers(cerebro)
    add_strategy_analyzers(cerebro)

    import datetime
    fromdate = datetime.datetime(2020, 1, 1)
    todate = datetime.datetime(2023, 1, 1)
    intrvl = '1d'

    for symbol in params['symbols']:
        df = bt.feeds.PandasData(dataname=yf.download(symbol, fromdate, todate, interval=intrvl, prepost=True, threads=True, auto_adjust=True))
        cerebro.adddata(df)
        #df.addfilter(bt.filters.HeikinAshi) #add filters to data

    def add_strategy_settings(cerebro,**params):
        #error params arent updated here - initial param from base still wors, so is loggings een after diabled
        #initial cash of 0 kept in base is still used to calculate pnl,
        #moreover 100000 iinit_cash in params is not taen and bactrader default of 100000 is taen in strategy
        #AREA 1 TO ADD SETTINGS RELATED TO STRATEGIES
        for(key,value)in params.items():setattr(cerebro,key,value)
        init_cash=params.get('init_cash', {})
        cerebro.broker.set_cash(init_cash)
        cerebro.broker.set_coc(True)
        cerebro.broker.setcommission(0.01)
        cerebro.broker.set_slippage_perc(0.005)
        cerebro.addsizer(bt.sizers.AllInSizerInt, percents=100)

    cerebro.addstrategy(RSIStrategy, params)
    #cerebro.addstrategy(MACDStrategy)

    results = cerebro.run(**params)

#AREA 2 TO ADD parameters to the related settings we added in startegy settings
#params={'symbols':['SPY','TSLA'],'dates':['2022-01-01','2023-01-01'],'strategies':['rsi','macd'],'init_cash':100000,'buy_prop':1,'sell_prop':1,'fractional':False,'slippage':.001,'single_position':None,'commission':.001,'stop_loss':0,'stop_trail':0,'take_profit':0,'execution_type':'close','periodic_logging':False,'transaction_logging':False,'strategy_logging':False,'plot':True,'channel':'','allow_short':True,'short_max':1.5,'add_cash_amount':0,'add_cash_freq':'M','invest_div':True,'verbose':1,'sort_by':'rnorm','sentiments':[],'return_history':False,'return_plot':True,'channel':'','allow_short':True,'short_max':2,'figsize':(30,15),'multi_line_indicators':None,'data_class':None,'data_format_dict':None,'data_kwargs':None,'plot_kwargs':{},'fig':None}
params = {
    "symbols": ["SPY", "TSLA"],
    "dates": ["2022-01-01", "2023-01-01"],
    "strategies": ["rsi", "macd"],
    "init_cash": 100000,
    "buy_prop": 1,
    "sell_prop": 1,
    "fractional": False,
    "slippage": 0.001,
    "single_position": None,
    "commission": 0.001,
    "stop_loss": 0,
    "stop_trail": 0,
    "take_profit": 0,
    "execution_type": "close",
    "periodic_logging": False,
    "transaction_logging": True,
    "strategy_logging": True,
    "plot": True,
    "channel": "",
    "allow_short": True,
    "short_max": 1.5,
    "add_cash_amount": 0,
    "add_cash_freq": "M",
    "invest_div": True,
    "verbose": 1,
    "sort_by": "rnorm",
    "sentiments": [],
    "return_history": False,
    "return_plot": True,
    "channel": "",
    "allow_short": True,
    "short_max": 2,
    "figsize": (30, 15),
    "multi_line_indicators": None,
    "data_class": None,
    "data_format_dict": None,
    "data_kwargs": None,
    "plot_kwargs": {},
    "fig": None,
}


result=backtest(params=params)
