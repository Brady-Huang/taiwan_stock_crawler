# 台灣上市股票分散式爬蟲系統

## 專案簡介

此專案旨在建立一個**分散式網路爬蟲系統**，用於定期抓取台灣證券交易所（TWSE）的上市股票交易資料。系統採用 **Apache Airflow** 進行任務編排，**MySQL** 和 **Redis** 分別作為持久化儲存和快取層。專案涵蓋了完整的開發生命週期，包括 **Poetry** 進行套件管理、**CI/CD** (GitHub Actions) 流程、**單元測試**，並提供 **FastAPI** 介面供終端使用者查詢資料。

## 專案特色

*   **分散式架構**: 透過 Airflow 實現任務排程與分散式執行。
*   **資料來源**: 抓取台灣證券交易所的每日上市股票交易資料。
*   **資料儲存**: 
    *   **MySQL**: 用於持久化儲存歷史股票交易數據。
    *   **Redis**: 作為快取層，加速 API 查詢響應速度。
*   **API 服務**: 使用 FastAPI 建立高效能的 RESTful API，提供股票資料查詢服務。
*   **自動化與測試**: 
    *   **Poetry**: 現代化的 Python 套件管理工具。
    *   **單元測試**: 確保爬蟲邏輯和資料處理的正確性。
    *   **CI/CD**: 透過 GitHub Actions 自動化測試和部署流程。

## 系統架構圖

```mermaid
graph TD
    A[TWSE Website] --> B(Python Crawler)
    B --> C{Data Processing}
    C --> D[Redis Cache]
    C --> E[MySQL Database]
    F[Airflow Scheduler] --> B
    G[FastAPI] --> D
    G --> E
    H[End User] --> G
    I[GitHub Actions] --> J[Tests]
    I --> K[Deployment]
    B -- uses --> Poetry
    G -- uses --> Poetry
```

## 環境設定

### 前置條件

在運行此專案之前，請確保您的系統已安裝以下軟體：

*   Python 3.11+
*   Poetry
*   Docker 及 Docker Compose (推薦用於 Airflow, MySQL, Redis)

### 專案安裝

1.  **複製專案**: 
    ```bash
    git clone https://github.com/your-username/taiwan-stock-crawler.git
    cd taiwan-stock-crawler
    ```

2.  **安裝 Poetry 依賴**: 
    ```bash
    poetry install
    ```

3.  **環境變數設定**: 
    建立 `.env` 檔案於專案根目錄，並填入資料庫和 Redis 連線資訊：
    ```dotenv
    # MySQL Configuration
    MYSQL_USER=root
    MYSQL_PASSWORD=your_mysql_password
    MYSQL_HOST=localhost
    MYSQL_PORT=3306
    MYSQL_DB=taiwan_stock

    # Redis Configuration
    REDIS_HOST=localhost
    REDIS_PORT=6379
    REDIS_DB=0
    ```

### 使用 Docker Compose 啟動服務 (推薦)

為了方便部署 Airflow, MySQL 和 Redis，我們提供了一個 `docker-compose.yml` 檔案。請先建立此檔案：

```yaml
version: '3.8'
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DB}
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

  redis:
    image: redis:latest
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  airflow-scheduler:
    build: .
    command: scheduler
    restart: always
    environment:
      - AIRFLOW_HOME=/opt/airflow
      - AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags
      - AIRFLOW__CORE__LOAD_EXAMPLES=False
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=mysql+pymysql://root:${MYSQL_PASSWORD}@mysql:3306/${MYSQL_DB}
      - AIRFLOW__CELERY__BROKER_URL=redis://redis:6379/0
      - AIRFLOW__CELERY__RESULT_BACKEND=db+mysql+pymysql://root:${MYSQL_PASSWORD}@mysql:3306/${MYSQL_DB}
      - AIRFLOW__WEBSERVER__SECRET_KEY=super-secret
      - MYSQL_USER=${MYSQL_USER}
      - MYSQL_PASSWORD=${MYSQL_PASSWORD}
      - MYSQL_HOST=mysql
      - MYSQL_PORT=3306
      - MYSQL_DB=${MYSQL_DB}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_DB=${REDIS_DB}
    volumes:
      - ./dags:/opt/airflow/dags
      - ./src:/opt/airflow/src
      - ./tests:/opt/airflow/tests
      - ./pyproject.toml:/opt/airflow/pyproject.toml
      - ./poetry.lock:/opt/airflow/poetry.lock
    depends_on:
      - mysql
      - redis

  airflow-webserver:
    build: .
    command: webserver
    restart: always
    environment:
      - AIRFLOW_HOME=/opt/airflow
      - AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags
      - AIRFLOW__CORE__LOAD_EXAMPLES=False
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=mysql+pymysql://root:${MYSQL_PASSWORD}@mysql:3306/${MYSQL_DB}
      - AIRFLOW__CELERY__BROKER_URL=redis://redis:6379/0
      - AIRFLOW__CELERY__RESULT_BACKEND=db+mysql+pymysql://root:${MYSQL_PASSWORD}@mysql:3306/${MYSQL_DB}
      - AIRFLOW__WEBSERVER__SECRET_KEY=super-secret
      - MYSQL_USER=${MYSQL_USER}
      - MYSQL_PASSWORD=${MYSQL_PASSWORD}
      - MYSQL_HOST=mysql
      - MYSQL_PORT=3306
      - MYSQL_DB=${MYSQL_DB}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_DB=${REDIS_DB}
    ports:
      - "8080:8080"
    volumes:
      - ./dags:/opt/airflow/dags
      - ./src:/opt/airflow/src
      - ./tests:/opt/airflow/tests
      - ./pyproject.toml:/opt/airflow/pyproject.toml
      - ./poetry.lock:/opt/airflow/poetry.lock
    depends_on:
      - mysql
      - redis

  fastapi-app:
    build: .
    command: bash -c "poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    restart: always
    environment:
      - MYSQL_USER=${MYSQL_USER}
      - MYSQL_PASSWORD=${MYSQL_PASSWORD}
      - MYSQL_HOST=mysql
      - MYSQL_PORT=3306
      - MYSQL_DB=${MYSQL_DB}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_DB=${REDIS_DB}
    ports:
      - "8000:8000"
    depends_on:
      - mysql
      - redis

volumes:
  mysql_data:
  redis_data:
```

同時，需要一個 `Dockerfile` 來構建 Airflow 和 FastAPI 服務的映像：

```dockerfile
FROM python:3.11-slim-bookworm

WORKDIR /opt/airflow

# Install Poetry
RUN pip install poetry

# Copy project files
COPY pyproject.toml poetry.lock ./ 
COPY dags ./dags
COPY src ./src
COPY tests ./tests

# Install dependencies
RUN poetry install --no-root --no-interaction --no-dev

# Airflow specific setup
ENV AIRFLOW_HOME=/opt/airflow
ENV PYTHONPATH=/opt/airflow:$PYTHONPATH

# Initialize Airflow DB
RUN airflow db init
RUN airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

EXPOSE 8080 8000
```

然後執行：

```bash
docker compose up -d
```

### 手動啟動服務

1.  **啟動 MySQL 和 Redis 服務** (請確保它們已正確安裝並運行)。

2.  **運行爬蟲 (手動觸發)**: 
    ```bash
    poetry run python -c "from src.crawler.twse_crawler import twse_stock_crawler; from src.database.db_manager import DBManager; import datetime; df = twse_stock_crawler(datetime.date.today().strftime('%Y%m%d')); db = DBManager(); db.save_to_mysql(df)"
    ```

3.  **啟動 FastAPI 服務**: 
    ```bash
    poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000
    ```
    API 文件將在 `http://localhost:8000/docs` 提供。

## 運行測試

```bash
poetry run pytest tests/
```

## CI/CD (GitHub Actions)

專案配置了 GitHub Actions，會在每次 `push` 或 `pull_request` 到 `main` 或 `master` 分支時自動執行測試和 Linting。配置檔案位於 `.github/workflows/ci.yml`。

## 貢獻

歡迎任何形式的貢獻！請先提交 Issue 討論您的想法，然後提交 Pull Request。

## 授權

此專案採用 MIT 授權條款。詳情請見 `LICENSE` 檔案。

