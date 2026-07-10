import pytest
import pandas as pd
from src.crawler.twse_crawler import zn2en_colname, clear_data, check_schema

def test_zn2en_colname():
    df = pd.DataFrame({
        '證券代號': ['2330'],
        '證券名稱': ['台積電'],
        '成交股數': ['1000']
    })
    colname = ['證券代號', '證券名稱', '成交股數']
    result = zn2en_colname(df, colname)
    assert 'symbol' in result.columns
    assert 'volume' in result.columns
    assert '證券名稱' not in result.columns

def test_clear_data():
    df = pd.DataFrame({
        'volume': ['1,000', '2,000', '---'],
        'open': ['100.5', 'X101.0', '--']
    })
    result = clear_data(df)
    assert result['volume'][0] == 1000
    assert result['volume'][2] == 0
    assert result['open'][1] == 101.0
    assert result['open'][2] == 0

def test_check_schema():
    data = {
        'symbol': '2330',
        'volume': 1000.0,
        'transaction': 10.0,
        'trade_value': 10000.0,
        'open': 100.0,
        'high': 105.0,
        'low': 99.0,
        'close': 102.0,
        'date': '2024-01-01'
    }
    df = pd.DataFrame([data])
    result = check_schema(df)
    assert len(result) == 1
    assert result.iloc[0]['symbol'] == '2330'
