import numpy as np
import requests
from bs4 import BeautifulSoup
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
nltk.download('vader_lexicon')
# import yfinance as yf
import finnhub
import pandas as pd
from alpaca.common.rest import RESTClient
import pandas as pd
from datetime import date, timedelta


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0;Win64) AppleWebkit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
}

# Alpaca - authentication and connection details
ALPACA_API_KEY = 'PKQ89N6MBAFGWQ44DDGX'
ALPACA_API_SECRET = '8qvyZ2pTScgnIl86Tn6VQJU3qb8KMT3RLzl4gzYJ'
BASE_URL =  'https://paper-api.alpaca.markets'  # Use 'https://api.alpaca.markets' for live trading

# Finnhub - authentication and connection details
FIN_API_KEY = 'ch08f99r01qt0s72chngch08f99r01qt0s72cho0'
finnhub_client = finnhub.Client(api_key=FIN_API_KEY)

# Date/time ranges
end_date = date.today()
duration = 7
start_date = end_date - timedelta(days=duration)

def scrape_headlines(ticker):

    iso_start_date = start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    iso_end_date = end_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    news_client = RESTClient(base_url='https://data.alpaca.markets',
                         api_version='v1beta1',
                         api_key=ALPACA_API_KEY, 
                         secret_key=ALPACA_API_SECRET,)

    news_endpoint = '/news'
    parameters = {'start':iso_start_date,
                'end':iso_end_date,
                'symbols':ticker,
    }

    news = news_client.get(news_endpoint, parameters,)
    next_page_token = news.get('next_page_token')

    df = pd.DataFrame.from_dict(news['news'])

    while next_page_token:
        parameters['page_token'] = next_page_token
        news = news_client.get(news_endpoint, parameters,)
        next_page_token = news.get('next_page_token')
        df = pd.concat([df, pd.DataFrame.from_dict(news['news'])], ignore_index=True)
        if not next_page_token:
            break
    

    df['headline'].to_csv('histnews.csv', index=False)

    headlines = df['headline'].tolist()
    headlines = headlines[1:]

    return headlines

def sentiment_analysis(headlines):
    analyzer = SentimentIntensityAnalyzer()
    scores = [analyzer.polarity_scores(h)["compound"] for h in headlines]
    return sum(scores) / len(scores)

def fundamental_analysis(ticker):
    # Pattern recognition)
    recommendation_data = finnhub_client.recommendation_trends(ticker)
    num_ratings = 0
    overall_rating = 0
    for x in recommendation_data:
        num_ratings += x['buy']+x['strongBuy']+x['hold']+x['strongSell']+x['sell']
    
    for x in recommendation_data:
        overall_rating += (x['strongBuy']+x['buy']+(x['hold']*(-.5))+(x['sell']*(-1))+(x['strongSell']*(-1)))/num_ratings
    overall_rating = overall_rating/len(recommendation_data)

    # buy_percent = (recommendation_data['buy']+recommendation_data['strongBuy'])/num_ratings
    
    # average % earnings are beating estimates
    earnings_data = finnhub_client.company_earnings(ticker)
    earnings_differential = []
    for x in earnings_data:
        if x['surprisePercent'] != None:
            earnings_differential.append(x['surprisePercent'])
    
    average_surprise = sum(earnings_differential) / len(earnings_differential)
    # make it a score from -1 to 1
    average_surprise = average_surprise/100

    fund_score = (overall_rating*(.5)) + (average_surprise*(.5))

    return fund_score

def social_sentiment_analysis(ticker):
    # Get the social sentiment score - reddit, tweets, etc.
    social_sentiment = finnhub_client.stock_social_sentiment(ticker)
    # score from -1 to 1, negative to positive
    media_data = []
    for x in social_sentiment:
        if len(x) > 6:
            try:
                media_data.append(social_sentiment[x]['score'])
            except:
                print(f"Note: {x} does not have any data. Skipped.")
    
    if media_data != []:
        socialmedia_score = sum(media_data) / len(media_data)
    else:
        socialmedia_score = 0
        print("Social sentiment analysis unavailable for this company.")

    return socialmedia_score

def combine_analysis(sentiment, fund_score, social_score, tech_score):
    sentiment_weight = .25
    fund_weight = .25
    social_weight = .25
    tech_weight = .25

    # if no social media analysis applies then re-weight
    if social_score == 0:
        social_weight = 0
        sentiment_weight = .33
        fund_weight = .33
        tech_weight = .33
    # if no technical analysis applies then re-weight
        if tech_score == 0:
            tech_weight = 0
            sentiment_weight = .5
            fund_weight = .5
    # vice versa
    # if no technical analysis applies then re-weight
    elif tech_score == 0:
        tech_weight = 0
        sentiment_weight = .33
        fund_weight = .33
        social_weight = .33
    # if no social media analysis applies then re-weight
        if social_score == 0:
            social_weight = 0
            sentiment_weight = .5
            fund_weight = .5

    # Determine the overall score based on the sentiment and chart patterns
    score = (sentiment * sentiment_weight) + (fund_score * fund_weight) + (social_score * social_weight) + (tech_score * tech_weight)

    # Return the recommendation based on the overall score
    print(f"Final weighted score is: {score}")
    if score > 0:
        return "BUY"
    else:
        return "SELL"

ticker = input("Enter a company ticker: ")
headlines = scrape_headlines(ticker)

mean_sentiment = sentiment_analysis(headlines)
fund_score = fundamental_analysis(ticker)
social_score = social_sentiment_analysis(ticker)
tech_score = 0

recommendation = combine_analysis(mean_sentiment, fund_score, social_score, tech_score)

print(f"The mean sentiment of the headlines for {ticker} is {mean_sentiment}.")
print(f"The fundamental analysis score of {ticker} is {fund_score}.")
print(f"The social sentiment score of {ticker} is {social_score}.")
print(f"The technical analysis score of {ticker} is {tech_score}.")

print(recommendation)