import requests
import pandas as pd
import backtrader as bt
import yfinance as yf
from datetime import datetime

def get_yfinance_data():
	symbol = "AAPL"
	start_date = "2021-01-01"
	end_date = "2021-12-31"

	data = yf.download(symbol, start=start_date, end=end_date)
	data.to_csv("temp.csv")

if __name__ == "__main__":
	get_yfinance_data()