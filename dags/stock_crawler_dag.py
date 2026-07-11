from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os
import logging

# 確保 Airflow 能正確抓到你的 src 資料夾
# 在 Docker 環境中，/opt/airflow 是預設的工作目錄
sys.path.append('/opt/airflow')

from src.crawler.twse_crawler import twse_stock_crawler
from src.database.db_manager import DBManager

# 設定 Logging，讓 Airflow 介面的 Log 更清楚
logger = logging.getLogger(__name__)

# 1. 定義生產環境的預設參數
default_args = {
    'owner': 'brady.huang',
    'depends_on_past': False,         # 不依賴前一次任務是否成功，失敗也能跑隔天的
    'start_date': datetime(2026, 7, 1), # 設定補課的起始日期
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,                     # ⚠️ 生產級必備：失敗自動重試 3 次 (應對 API 不穩)
    'retry_delay': timedelta(minutes=5), # 每次重試間隔 5 分鐘
}

def crawl_and_save(ds, **kwargs):
    """
    ds: Airflow 自動傳入的執行日期 (YYYY-MM-DD)
    """
    # 將 YYYY-MM-DD 格式轉為證交所需要的 YYYYMMDD
    date_str = ds.replace('-', '')
    
    logger.info(f"--- 開始執行生產級爬蟲任務，目標日期：{date_str} ---")
    
    try:
        # 執行爬蟲
        df = twse_stock_crawler(date_str)
        
        if df is not None and not df.empty:
            # 只有在有資料時才初始化 DBManager 並存檔
            db = DBManager()
            db.save_to_mysql(df)
            logger.info(f"✅ 日期 {date_str}：成功處理並 Upsert {len(df)} 筆資料。")
        else:
            # 週末或國定假日證交所沒資料，這在生產環境是正常情況
            logger.info(f"ℹ️ 日期 {date_str}：證交所無資料 (可能為休市日)。")
            
    except Exception as e:
        logger.error(f"❌ 日期 {date_str} 執行過程中發生錯誤: {str(e)}")
        # 拋出異常，讓 Airflow 觸發 retries 機制
        raise e

# 2. 定義 DAG 本體
with DAG(
    'taiwan_stock_daily_crawler_prod', # 建議改名區分測試版
    default_args=default_args,
    description='生產級別：台灣股市每日收盤行情爬蟲',
    schedule_interval='0 18 * * 1-5',   # ⚠️ 每週一至五，台北時間傍晚 18:00 執行
    catchup=True,                     # ⚠️ 生產級功能：自動補足從 start_date 到今天的所有資料
    max_active_runs=1,                # ⚠️ 確保同時只有一個任務在跑，避免 API 被鎖 IP
    tags=['production', 'finance', 'twse'],
) as dag:

    # 3. 定義任務
    crawl_task = PythonOperator(
        task_id='crawl_twse_stock',
        python_callable=crawl_and_save,
        # ds 變數會自動透過 kwargs 傳入 crawl_and_save
    )

    # 如果未來有分析任務，可以在這邊串接 (例如 crawl_task >> analysis_task)
    crawl_task
