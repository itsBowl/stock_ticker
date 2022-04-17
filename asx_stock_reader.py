"""
Mostly just for me here :D
Some explainers:
'print(f"test")' is a c-style formatting trick that allows me to load variables into a print functions inline with the text.
It's just a shorter hand way of building print lines that's faster to write than using other methods
print("text", end="") is a pythonic way of setting the trailing character of a print function. Normal python functionality sets
the end of the print function to print a newline character (\n), you can instead specifiy a different character including no character.

"""

import datetime
from pandas import ExcelWriter
import pandas as pd
from pandas_datareader import data as pdr
import requests
import csv
import time

start_date = datetime.datetime.now() - datetime.timedelta(days=365)
end_date = datetime.date.today()
tickers = []
exportList = pd.DataFrame(columns=['Stock', "RS_Rating", "50 Day MA", "150 Day Ma", "200 Day MA", "52 Week Low", "52 week High"])
returns_multiples = []
index_name = "^AXKO"


def get_asx_all_ords_tickers():
    url = "https://www.stockmetric.net/asx-indices/all-ordinaries/"
    #Tricks the server into sending us the data as it regects non-browser based requests for data
    header = {
      "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.75 Safari/537.36",
      "X-Requested-With": "XMLHttpRequest"
    }
    print("Sending HTML Request")
    
    #Gets the entire contents of the webpage as HTML, loads it into memory as local variable request
    request = requests.get(url, headers=header) 
    print(f"Got html from {url}")

    table = pd.read_html(request.text)[1]
    table.info()
    tickers = table.iloc[:, 0]
    tickers_fixed = []
    for i in tickers:
        tickers_fixed.append(i + ".AX")
    return tickers_fixed


tickers = get_asx_all_ords_tickers()
"""Uncomment  below for debugging of fetched data ticker symbols"""
#for i in tickers:
#    print(i)

index_df = pdr.get_data_yahoo(index_name, start_date, end_date)
index_df['Percent Change'] = index_df['Adj Close'].pct_change()
index_return = (index_df['Percent Change'] + 1).cumprod()[-1]
counter = 0
print(f'index return for market {index_return}')
tickers_fail = []
for ticker in tickers:
    print(ticker)
    if counter == 0:
        counter += 1
        continue
    try:
        df = pdr.get_data_yahoo(ticker, start_date, end_date)
    except Exception:
        print(f"Failed to get data for stock {ticker}, moving on\n")
        tickers_fail.append(ticker)
        continue
    try:
        df.to_csv(f'{ticker}.csv')
    except Exception:
        print(f"Failed to save data for stock {ticker}, moving on\n")
        tickers_fail.append(ticker)
        continue

    df['Percent Change'] = df['Adj Close'].pct_change()
    stock_return = (df['Percent Change'] + 1).cumprod()[-1]

    returns_multiple = round((stock_return / index_return), 2)
    returns_multiples.extend([returns_multiple])
    
    print (f'Ticker: {ticker}; Returns Multiple against All Ords: {returns_multiple}\n')
    time.sleep(0.8)


#making top 30% dataframe
rs_df = pd.DataFrame(list(zip(tickers, returns_multiples)), columns=['Ticker', 'Returns_multiple'])
rs_df['RS_Rating'] = rs_df.Returns_multiple.rank(pct=True) * 100
rs_df = rs_df[rs_df.RS_Rating >= rs_df.RS_Rating.quantile(.70)]

rs_stocks = rs_df['Ticker']
for stock in rs_stocks:
    try:
        df = pd.read_csv(f'{stock}.csv', index_col=0)
        sma = [50, 150, 200]
        for x in sma:
            df["SMA_"+str(x)] = round(df["Adj Close"].rolling(window=x).mean(), 2)

        #Sorting required values
        currentClose = df["Adj Close"][-1]
        moving_average_50 = df["SMA_50"][-1]
        moving_average_150 = df["SMA_150"][-1]
        moving_average_200 = df["SMA_200"][-1]
        low_of_52week = round(min(df["Low"][-260:]), 2)
        high_of_52week = round(max(df["High"][-260:]), 2)
        RS_Rating = round(rs_df[rs_df['Ticker']==stock].RS_Rating.tolist()[0])
        
        try:
            moving_average_200_20 = df["SMA_200"][-20]
        except Exception:
            moving_average_200_20 = 0

        # Condition 1: Current Price > 150 SMA and > 200 SMA
        condition_1 = currentClose > moving_average_150 > moving_average_200
        
        # Condition 2: 150 SMA and > 200 SMA
        condition_2 = moving_average_150 > moving_average_200

        # Condition 3: 200 SMA trending up for at least 1 month
        condition_3 = moving_average_200 > moving_average_200_20
        
        # Condition 4: 50 SMA> 150 SMA and 50 SMA> 200 SMA
        condition_4 = moving_average_50 > moving_average_150 > moving_average_200
           
        # Condition 5: Current Price > 50 SMA
        condition_5 = currentClose > moving_average_50
           
        # Condition 6: Current Price is at least 30% above 52 week low
        condition_6 = currentClose >= (1.3*low_of_52week)
           
        # Condition 7: Current Price is within 25% of 52 week high
        condition_7 = currentClose >= (.75*high_of_52week)
        
        # If all conditions above are true, add stock to exportList
        if(condition_1 and condition_2 and condition_3 and condition_4 and condition_5 and condition_6 and condition_7):
            exportList = exportList.concat({'Stock': stock, "RS_Rating": RS_Rating ,"50 Day MA": moving_average_50, "150 Day Ma": moving_average_150, "200 Day MA": moving_average_200, "52 Week Low": low_of_52week, "52 week High": high_of_52week}, ignore_index=True)
            print (stock + " made the Minervini requirements")

    except Exception as e:
        print(e)
        print(f"Could not gather data on stock {stock}")

exportList = exportList.sort_values(by='RS_Rating', ascending=False)
print('\n', exportList)
writer = ExcelWriter("ScreenOutput.xlsx")
exportList.to_excel(writer, "Sheet1")
tickers_fail.to_excel(writer, "Sheet2")
writer.save()


"""
Time worked:
4hrs on call 10/04
4hrs between calls so far


"""