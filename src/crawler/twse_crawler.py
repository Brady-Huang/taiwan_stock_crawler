import datetime as dt
import time
import json
import random
import pandas as pd
import requests
from pydantic import BaseModel
from typing import Optional

class TaiwanStockPrice(BaseModel):
    symbol: str
    volume: float
    transaction: float
    trade_value: float
    open: float
    high: float
    low: float
    close: float
    date: str

def twse_headers():
    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "referer": "https://www.twse.com.tw/zh/trading/historical/mi-index.html",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
        "Host": "www.twse.com.tw",
        "Connection": "keep-alive"
    }
    return headers

def zn2en_colname(df, colname):
    zn_en_dict = {
        '證券代號': 'symbol',
        '證券名稱': '', 
        '成交股數': 'volume', 
        '成交筆數': 'transaction', 
        '成交金額': 'trade_value', 
        '開盤價': 'open', 
        '最高價': 'high', 
        '最低價': 'low', 
        '收盤價': 'close',
        '漲跌(+/-)': '', 
        '漲跌價差': "", 
        '最後揭示買價': '', 
        '最後揭示買量': '', 
        '最後揭示賣價': '', 
        '最後揭示賣量': '', 
        '本益比': ''
    }
    
    df.columns = [zn_en_dict.get(col, '') for col in colname]
    if '' in df.columns:
        df = df.drop([''], axis=1)
    return df

def clear_data(df):
    df = df.fillna('')
    cols_to_fix = ['volume', 'transaction', 'trade_value', 'open', 'high', 'low', 'close']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = (df[col].astype(str)
                       .str.replace(",", "")
                       .str.replace("X", "")
                       .str.replace("+", "")
                       .str.replace("----", "0")
                       .str.replace("---", "0")
                       .str.replace("--", "0")
                      )
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def check_schema(df):
    df_dict = df.to_dict("records")
    df_schema = []
    for dd in df_dict:
        try:
            df_schema.append(TaiwanStockPrice(**dd).model_dump())
        except Exception as e:
            print(f"Schema validation error for {dd.get('symbol')}: {e}")
            continue
    return pd.DataFrame(df_schema)

def twse_stock_crawler(date: str) -> pd.DataFrame:
    # date format: YYYYMMDD
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={date}&type=ALLBUT0999&response=json"
    
    # avoid frequent request
    time.sleep(random.randint(5, 7))
    
    try:
        res = requests.get(url, headers=twse_headers(), timeout=30)
        data = res.json()
        
        if data.get('stat') == '很抱歉，沒有符合條件的資料!':
            return pd.DataFrame()
            
        if "tables" in data:
            # Table 8 is usually the stock price table
            # We should find the table that contains '證券代號'
            target_table = None
            for table in data['tables']:
                if '證券代號' in table.get('fields', []):
                    target_table = table
                    break
            
            if target_table:
                df = pd.DataFrame(target_table['data'])
                col_name = target_table['fields']
                df = zn2en_colname(df.copy(), col_name)
                df = clear_data(df)
                df['date'] = f"{date[:4]}-{date[4:6]}-{date[6:]}"
                return check_schema(df)
                
    except Exception as e:
        print(f"Crawler error for date {date}: {e}")
        
    return pd.DataFrame()
