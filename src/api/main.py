from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
import pandas as pd
from datetime import date
from src.database.db_manager import DBManager, StockPrice
from sqlalchemy.orm import Session
from sqlalchemy import select

app = FastAPI(title="Taiwan Stock API")
db_manager = DBManager()

@app.get("/")
def read_root():
    return {"message": "Welcome to Taiwan Stock Crawler API"}

@app.get("/stock/{symbol}", response_model=List[dict])
def get_stock_price(
    symbol: str, 
    start_date: Optional[date] = None, 
    end_date: Optional[date] = None
):
    # Try to get from cache first
    cache_key = f"stock_{symbol}_{start_date}_{end_date}"
    cached_data = db_manager.get_from_cache(cache_key)
    if cached_data:
        return cached_data

    # Query from MySQL
    with db_manager.SessionLocal() as session:
        query = select(StockPrice).where(StockPrice.symbol == symbol)
        if start_date:
            query = query.where(StockPrice.date >= start_date)
        if end_date:
            query = query.where(StockPrice.date <= end_date)
        
        result = session.execute(query).scalars().all()
        
        if not result:
            raise HTTPException(status_code=404, detail="Stock data not found")
        
        # Convert to list of dicts
        data = [
            {
                "symbol": r.symbol,
                "date": str(r.date),
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
                "transaction": r.transaction,
                "trade_value": r.trade_value
            } for r in result
        ]
        
        # Save to cache
        db_manager.set_cache(cache_key, data)
        
        return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
