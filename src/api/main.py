from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
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

@app.get("/health")
def health():
    return {"status": "ok"}

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

@app.get("/chart/{symbol}", response_class=HTMLResponse)
def get_stock_chart(symbol: str):
    # 先查資料
    with db_manager.SessionLocal() as session:
        query = select(StockPrice).where(StockPrice.symbol == symbol).order_by(StockPrice.date)
        result = session.execute(query).scalars().all()
        
        if not result:
            return HTMLResponse("<h1>No data found</h1>", status_code=404)
        
        dates = [str(r.date) for r in result]
        closes = [r.close for r in result]
        opens = [r.open for r in result]
        highs = [r.high for r in result]
        lows = [r.low for r in result]

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{symbol} 股價走勢</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
            h1 {{ color: #333; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{symbol} 股價走勢</h1>
            <canvas id="stockChart"></canvas>
        </div>
        <script>
            const ctx = document.getElementById('stockChart').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: {dates},
                    datasets: [
                        {{
                            label: '收盤價',
                            data: {closes},
                            borderColor: 'rgb(75, 192, 192)',
                            tension: 0.1,
                            fill: false
                        }},
                        {{
                            label: '開盤價',
                            data: {opens},
                            borderColor: 'rgb(255, 159, 64)',
                            tension: 0.1,
                            fill: false
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{ position: 'top' }},
                        title: {{
                            display: true,
                            text: '{symbol} 股價走勢圖'
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
