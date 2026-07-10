import os
import redis
import json
import logging
import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Column, String, Float, Date
from sqlalchemy.dialects.mysql import insert as mysql_insert # 導入 MySQL 特有的 insert
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "test")
MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql") 
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "taiwan_stock")

DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

Base = declarative_base()

class StockPrice(Base):
    __tablename__ = "stock_prices"
    id = Column(String(50), primary_key=True)
    symbol = Column(String(20), index=True)
    date = Column(Date, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    transaction = Column(Float)
    trade_value = Column(Float)

class DBManager:
    def __init__(self):
        self._engine = create_engine(
            DATABASE_URL,
            pool_recycle=3600,
            pool_pre_ping=True
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True # 自動將 bytes 轉為 str
        )
        Base.metadata.create_all(bind=self._engine)

    @property
    def engine(self):
        return self._engine

    def save_to_mysql(self, df: pd.DataFrame):
        if df.empty:
            logger.warning("DataFrame is empty, skipping.")
            return
        
        try:
            df_copy = df.copy()
            df_copy['date'] = pd.to_datetime(df_copy['date']).dt.date
            df_copy['id'] = df_copy['symbol'].astype(str) + "_" + df_copy['date'].astype(str)
            
            db_columns = ['id', 'symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'transaction', 'trade_value']
            final_df = df_copy[df_copy.columns.intersection(db_columns)]
            data_to_insert = final_df.to_dict(orient='records')
            
            # --- 生產級 Upsert 邏輯 ---
            with self.engine.begin() as conn:
                stmt = mysql_insert(StockPrice).values(data_to_insert)
                
                # 如果 id 重複，更新以下欄位
                update_dict = {
                    c.name: stmt.inserted[c.name] 
                    for c in StockPrice.__table__.columns 
                    if c.name not in ['id', 'symbol', 'date'] # 這些欄位不更新
                }
                
                upsert_stmt = stmt.on_duplicate_key_update(**update_dict)
                conn.execute(upsert_stmt)
            
            logger.info(f"Successfully Upserted {len(final_df)} rows to MySQL.")

        except Exception as e:
            logger.error(f"Database Error: {str(e)}")
            raise e
    
    # --- Redis 封裝方法 ---
    def get_from_cache(self, key: str):
        data = self.redis_client.get(key)
        return json.loads(data) if data else None

    def set_cache(self, key: str, data: list, expire: int = 3600):
        # 存入時轉為 JSON 字串，並設定 1 小時過期以免佔用記憶體
        self.redis_client.setex(key, expire, json.dumps(data))