import requests
from bs4 import BeautifulSoup
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
nltk.download('vader_lexicon')
import talib
import yfinance as yf
import pandas as pd
from alpaca.data.live import StockDataStream
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime
import io


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0;Win64) AppleWebkit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
}

def scrape_headlines(ticker):
    url = f"https://finviz.com/quote.ashx?t={ticker}&p=d"
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    news_table = soup.find(id = 'news-table')
    rows = news_table.find_all('div', class_ = "news-link-left")
    headlines = []
    for row in news_table.find_all('div', class_ = "news-link-left"):
      headlines.append(row.text)
    return headlines

#     for row in rows:
#         headline = row.a.get_text()
#         date_data = row.td.text.split(' ')
#         if len(date_data) == 1:
#             time = date_data[0]
#         else:
#             date = date_data[0]
#             time = date_data[1]
#         parsed_data.append([ticker, date, time, headline])
#         headlines.append([headline])
#     return headlines

def sentiment_analysis(headlines):
    analyzer = SentimentIntensityAnalyzer()
    scores = [analyzer.polarity_scores(h)["compound"] for h in headlines]
    return sum(scores) / len(scores)

def technical_analysis(ticker):
    # Get historical stock data
    data = yf.download(ticker, start="2023-01-01")
    # Calculate technical indicators
    data["SMA20"] = talib.SMA(data["Close"], timeperiod=20)
    data["SMA50"] = talib.SMA(data["Close"], timeperiod=50)
    data["SMA200"] = talib.SMA(data["Close"], timeperiod=200)
    data["RSI"] = talib.RSI(data["Close"], timeperiod=14)
    data["MACD"], data["MACD_signal"], data["MACD_hist"] = talib.MACD(data["Close"], fastperiod=12, slowperiod=26, signalperiod=9)
    # Chart patterns
    chart_patterns = []
    if data["SMA20"].iloc[-1] > data["SMA50"].iloc[-1] > data["SMA200"].iloc[-1]:
        chart_patterns.append("Bullish golden cross")
    if data["RSI"].iloc[-1] > 70:
        chart_patterns.append("Overbought")
    if data["RSI"].iloc[-1] < 30:
        chart_patterns.append("Oversold")
    if data["MACD_hist"].iloc[-1] > 0:
        chart_patterns.append("Bullish MACD crossover")
    if data["MACD_hist"].iloc[-1] < 0:
        chart_patterns.append("Bearish MACD crossover")
    # Head and shoulders pattern
    prices = data["Close"].tolist()
    head_and_shoulders = False
    left_shoulder = prices[:len(prices)//3]
    head = prices[len(prices)//3:len(prices)*2//3]
    right_shoulder = prices[len(prices)*2//3:]
    if max(left_shoulder) < max(head) and max(head) > max(right_shoulder):
        head_and_shoulders = True
    if head_and_shoulders:
        chart_patterns.append("Head and shoulders")
    # Bollinger bands
    data["SMA"] = talib.SMA(data["Close"], timeperiod=20)
    data["upper_band"], data["middle_band"], data["lower_band"] = talib.BBANDS(
        data["Close"], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
    )
    if data["Close"].iloc[-1] > data["upper_band"].iloc[-1]:
        chart_patterns.append("Upper Bollinger band")
    if data["Close"].iloc[-1] < data["lower_band"].iloc[-1]:
        chart_patterns.append("Lower Bollinger band")
    # Double top and double bottom pattern
    prices = data["Close"].tolist()
    double_top_or_bottom = False
    first_top_or_bottom = prices[:len(prices)//2]
    second_top_or_bottom = prices[len(prices)//2:]
    if max(first_top_or_bottom) == max(second_top_or_bottom):
        double_top_or_bottom = True
        chart_patterns.append("Double top")
    if min(first_top_or_bottom) == min(second_top_or_bottom):
        double_top_or_bottom = True
        chart_patterns.append("Double bottom")
    # Exponential moving averages pattern
    data["EMA5"] = talib.EMA(data["Close"], timeperiod=5)
    data["EMA10"] = talib.EMA(data["Close"], timeperiod=10)
    data["EMA20"] = talib.EMA(data["Close"], timeperiod=20)
    if data["EMA5"].iloc[-1] > data["EMA10"].iloc[-1] > data["EMA20"].iloc[-1]:
        chart_patterns.append("Bullish EMA crossover")
    if data["EMA5"].iloc[-1] < data["EMA10"].iloc[-1] < data["EMA20"].iloc[-1]:
        chart_patterns.append("Bearish EMA crossover")
    # Triangle pattern
    highs = data["High"].tolist()
    lows = data["Low"].tolist()
    if max(highs) == min(lows):
        chart_patterns.append("Triangle pattern")
    # Return chart patterns, if any
    return chart_patterns

def technical_weight(chart_patterns):
    chart_pattern_weight = 0.25
    chart_bias = 0.0
    # bullish breakout pattern from a crossover involving short-term moving average breaking above its long-term moving average or resistance level
    if "Bullish golden cross" in chart_patterns:
        chart_bias += 0.4
    if "Overbought" in chart_patterns:
        chart_bias -= 0.5
    if "Oversold" in chart_patterns:
        chart_bias += 0.5
    # when the MACD line moves above the zero line to turn positive - when the 12-day EMA of the underlying security moves above the 26-day EMA
    if "Bullish MACD crossover" in chart_patterns:
        chart_bias += 0.2
    if "Bearish MACD crossover" in chart_patterns:
    # when the MACD moves below the zero line to turn negative - when the 12-day EMA moves below the 25-day EMA
        chart_bias -= 0.2
    # A reversal in the trend, in which the market moves from bullish to bearish
    if "Head and shoulders" in chart_patterns:
        chart_bias -= 0.3
    # If close price continuously touches Upper Bollinger band then the stock is overbought
    if "Upper Bollinger band" in chart_patterns:
        chart_bias -= 0.2
    # If close price continuously touches Lower Bollinger band then the stock is oversold
    if "Lower Bollinger band" in chart_patterns:
        chart_bias += 0.2
    # extremely bearish technical reversal pattern that forms after an asset reaches a high price two consecutive times with a moderate decline between the two highs. It is confirmed once the asset's price falls below a support level equal to the low between the two prior highs
    if "Double top" in chart_patterns:
        chart_bias -= 0.3
    # signal for possibility of new upward trend - bullish movement
    if "Double bottom" in chart_patterns:
        chart_bias += 0.3
    # occurs when a short-term EMA crosses above the long-term EMA
    if "Bullish EMA crossover" in chart_patterns:
      chart_bias += 0.2
    # occurs when a short-term EMA crosses below the long-term EMA
    if "Bearish EMA crossover" in chart_patterns:
      chart_bias -= 0.2
    # 
    if "Triangle pattern" in chart_patterns:
      chart_bias += 0.1
    # Institutional traders use: fibonacci levels, trendlines, simple horizontal support/resistance
    return chart_pattern_weight * chart_bias

def fundamental_analysis(ticker):
    fundamental_weight = 0.25
    fundamental_bias = 0.0

    API_KEY = 'CK9LHUCR54R27MEMS679'
    API_SECRET = 'w7CUdI8w9FjZfC0CBiFQ3tfyiQh1aBoYxjaiccCv'
    BASE_URL = 'https://paper-api.alpaca.markets'

    # Create an instance of the Alpaca API
    client = StockHistoricalDataClient(API_KEY, API_SECRET)

    request_params = StockBarsRequest(
        symbol_or_symbols = [ticker],
        timeframe=TimeFrame.Day,
        start=datetime.strptime("2022-07-01", '%Y-%m-%d')
    )

    bars = client.get_stock_bars(request_params)

    # convert to dataframe
    stock_df = bars.df
    print(stock_df)
    # Calculate ratios
    # pe_ratio = stock_df['pe_ratio']
    # pb_ratio = asset.pb_ratio

    # Fetch financial statements
    api_key_fmp = '94a1d1dbe221b6b49699874474c793e5'
    url_bs = f'https://financialmodelingprep.com/api/v3/financials/balance-sheet-statement/{ticker}?apikey={api_key_fmp}'
    url_is = f'https://financialmodelingprep.com/api/v3/financials/income-statement/{ticker}?apikey={api_key_fmp}'
    url_cf = f'https://financialmodelingprep.com/api/v3/financials/cash-flow-statement/{ticker}?apikey={api_key_fmp}'

    bs_data = requests.get(url_bs).json()
    bs_df = pd.DataFrame(bs_data['financials'])
    bs_df.set_index('date', inplace=True)

    is_data = requests.get(url_is).json()
    is_df = pd.DataFrame(is_data['financials'])
    is_df.set_index('date', inplace=True)

    cf_data = requests.get(url_cf).json()
    cf_df = pd.DataFrame(cf_data['financials'])
    cf_df.set_index('date', inplace=True)

    # Fetch competitors/industry
    url_yahoo = f'https://finance.yahoo.com/quote/{ticker}/competitors?p={ticker}'
    html = requests.get(url_yahoo).content
    df_list = pd.read_html(html)
    competitors = df_list[0]['Symbol'].tolist()
    industry = df_list[0]['Industry'].tolist()[0]

    # Fetch earnings data
    earnings = api.get_earnings(ticker)
    if len(earnings) > 0:
        last_earnings = earnings[0]
        eps_actual = last_earnings.actual_eps
        eps_estimate = last_earnings.estimated_eps
        surprise_pct = last_earnings.surprise_percent
    else:
        eps_actual = eps_estimate = surprise_pct = None

    # Discounted cash flows
    url_yahoo_stats = f'https://finance.yahoo.com/quote/{ticker}/key-statistics?p={ticker}'
    html_stats = requests.get(url_yahoo_stats).content
    df_list_stats = pd.read_html(html_stats)
    market_cap_str = df_list_stats[0].iloc[0][1]
    if 'T' in market_cap_str:
      market_cap = float(market_cap_str.replace('T', '')) * 1e12
    elif 'B' in market_cap_str:
      market_cap = float(market_cap_str.replace('B', '')) * 1e9
    else:
      market_cap = float(market_cap_str.replace('M', '')) * 1e6

    # Fetch risk-free rate and market return
    url_yahoo_bond = 'https://finance.yahoo.com/bonds'
    html_bond = requests.get(url_yahoo_bond).content
    df_list_bond = pd.read_html(html_bond)
    risk_free_rate = df_list_bond[0].iloc[0][1] / 100
    market_return = df_list_bond[0].iloc[1][1] / 100

    # Calculate WACC and estimate intrinsic value
    cost_of_equity = market_return + (1.2 * (market_return - risk_free_rate))
    cost_of_debt = 0.03
    tax_rate = 0.21
    weight_of_equity = market_cap / (market_cap + bs_df.iloc[-1]['Total liabilities'])
    weight_of_debt = 1 - weight_of_equity
    wacc = (cost_of_equity * weight_of_equity) + (cost_of_debt * (1 - tax_rate) * weight_of_debt)
    free_cash_flows = cf_df.iloc[-1]['Free cash flow']
    intrinsic_value = free_cash_flows / (wacc - 0.01)

    # Print analysis
    # print(f'Ticker: {ticker}')
    # print(f'Industry: {industry}')
    # print(f'Competitors: {", ".join(competitors)}')
    # print(f'P/E ratio: {pe_ratio}')
    # print(f'P/B ratio: {pb_ratio}')
    # print(f'EPS actual: {eps_actual}')
    # print(f'EPS estimate: {eps_estimate}')
    # print(f'Surprise %: {surprise_pct}')
    # print(f'Intrinsic value: ${intrinsic_value:.2f}')

    return fundamental_weight * fundamental_bias

def combine_analysis(sentiment, chart_patterns):
    # Calculate the weights for the sentiment and chart pattern analysis
    sentiment_weight = 0.5
    tech_weight = technical_weight(chart_patterns)
    # Determine the overall score based on the sentiment and chart patterns
    score = (sentiment * sentiment_weight) + tech_weight

    # if no technical analysis applies then score is just sentiment
    if score == sentiment * sentiment_weight:
      score = score * 2

    # Return the recommendation based on the overall score
    
    print(score)
    if score > 0:
        return "BUY"
    else:
        return "SELL"

def buy_or_sell(ticker):
    # Get the sentiment score
    headlines = scrape_headlines(ticker)
    sentiment_score = sentiment_analysis(headlines)
    # Get the chart patterns
    chart_patterns = technical_analysis(ticker)
    # # Calculate the technical indicators
    return combine_analysis(sentiment_score,chart_patterns)

ticker = input("Enter a company ticker: ")
headlines = scrape_headlines(ticker)
mean_sentiment = sentiment_analysis(headlines)
# fund_weight = fundamental_analysis(ticker)
print(f"The mean sentiment of the headlines for {ticker} is {mean_sentiment}.")
chart_patterns = technical_analysis(ticker)
# print(f"The fundamental analysis score for {ticker} is {fund_weight}")
print(f"The chart patterns for {ticker} are: {chart_patterns}.")
recommendation = buy_or_sell(ticker)
print(recommendation)