# 台灣上市股票分散式爬蟲系統

真實資料來源的 Batch Pipeline，每日自動抓取台灣證券交易所（TWSE）股票收盤行情，透過 Apache Airflow CeleryExecutor 實現分散式任務排程，並提供 FastAPI 查詢介面與股價走勢圖表。

## 系統架構

**Pipeline 流程：**
```
TWSE API → Airflow DAG（CeleryExecutor）→ MySQL → FastAPI → Redis Cache → Client
```

### 架構圖

```
┌─────────────────────────────────────────────────────┐
│                   Airflow                           │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐ │
│  │Webserver │  │ Scheduler │  │  Celery Worker   │ │
│  └──────────┘  └─────┬─────┘  └────────┬─────────┘ │
│                      │                 │            │
│              ┌───────▼─────────────────▼──────┐    │
│              │     Redis（Celery Broker）       │    │
│              └───────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │      MySQL       │
              │  taiwan_stock    │
              │  airflow_meta    │
              └────────┬─────────┘
                       │
              ┌────────▼─────────┐     ┌─────────────┐
              │     FastAPI      │────▶│    Redis    │
              │  - Stock API     │◀────│   (Cache)   │
              │  - Chart (HTML)  │     └─────────────┘
              └────────┬─────────┘
                       │
              ┌────────▼─────────┐
              │     Browser      │
              │  (Chart.js 圖表) │
              └──────────────────┘
```

## 主要特色

**分散式架構**：Airflow CeleryExecutor + Redis broker，支援水平擴展 worker

**真實資料來源**：爬取台灣證券交易所每日收盤行情，包含開高低收、成交量、成交筆數、成交金額

**生產級 DAG 設計**：
- `catchup=True` 可自動補足指定起始日期後的所有歷史資料
- `max_active_runs=1` 避免同時打 API 被鎖 IP
- `retries=3` + `retry_delay=5min` 應對 API 不穩定
- 休市日自動跳過（週末、國定假日）

**Upsert 邏輯**：`ON DUPLICATE KEY UPDATE`，重複爬取不會產生重複資料

**Redis Cache**：FastAPI 查詢先走 Redis，cache miss 才查 MySQL，TTL 1 小時

**股價走勢圖表**：內建 Chart.js 圖表，直接瀏覽器查看任何股票的開盤價與收盤價走勢

**資料庫分離**：Airflow metadata（`airflow_metadata`）和業務資料（`taiwan_stock`）使用不同 DB

**GCP 部署**：Terraform 管理 GCP 資源，Secret Manager 管理敏感資訊，一鍵部署到 Google Cloud

## 元件說明

| 元件 | 工具 | 用途 |
|---|---|---|
| 任務排程 | Apache Airflow 2.11.0 | DAG 排程、任務編排 |
| 執行器 | CeleryExecutor | 分散式任務執行 |
| Message Broker | Redis | Celery task queue |
| Worker 監控 | Flower | 即時監控 worker 狀態 |
| 資料庫 | MySQL 8.0 | 持久化儲存股票資料 |
| 快取 | Redis | API 查詢結果快取 |
| API | FastAPI | 股票資料查詢介面 + 走勢圖表 |
| 視覺化 | Chart.js | 瀏覽器端股價走勢圖 |
| DB 管理 | phpMyAdmin | 資料庫視覺化管理 |
| IaC | Terraform | GCP 基礎設施管理 |
| 密碼管理 | GCP Secret Manager | 安全儲存敏感資訊 |

## 資料庫 Schema

```sql
CREATE TABLE stock_prices (
    id           VARCHAR(50) PRIMARY KEY,  -- Unique key: {symbol}_{date}
    symbol       VARCHAR(20),              -- Stock ticker, e.g. 2330
    date         DATE,                     -- Trading date
    open         FLOAT,                    -- Opening price (TWD)
    high         FLOAT,                    -- Highest price (TWD)
    low          FLOAT,                    -- Lowest price (TWD)
    close        FLOAT,                    -- Closing price (TWD)
    volume       FLOAT,                    -- Trading volume (shares)
    transaction  FLOAT,                    -- Number of transactions
    trade_value  FLOAT                     -- Total trading value (TWD)
);
```

## 快速開始（本機）

### 前置條件

- Docker + Docker Compose
- Git

### 環境變數設定

```bash
cp .env.example .env
# 修改 .env 裡的密碼（可直接使用預設值跑 demo）
```

### 設定爬蟲起始日期

修改 `dags/stock_crawler_dag.py`，設定你想要的歷史資料起始日期：

```python
start_date=datetime(2026, 1, 1),  # 改成你想要的起始日期
```

> ⚠️ DAG 設定 `catchup=True`，打開開關後 Airflow 會自動補跑從 `start_date` 到今天所有的交易日。起始日期設太早會跑很久，也可能被證交所鎖 IP，建議從近期開始。

### 啟動服務

```bash
git clone https://github.com/Brady-Huang/taiwan_stock_crawler.git
cd taiwan_stock_crawler

docker compose up -d
```

### 首次使用流程

1. 到 Airflow UI（http://localhost:8080）登入（帳號：`admin`，密碼：`admin`）
2. 找到 `taiwan_stock_daily_crawler_prod`，把左邊的 toggle **打開**
3. Airflow 會自動透過 catchup 補跑從 `start_date` 到今天所有錯過的交易日
4. 等 DAG 跑完（task 變綠色）
5. 到 API Docs（http://localhost:8000/docs）查詢股票資料，或直接看圖表

> **catchup vs backfill**
> - **catchup**（自動）：打開 DAG toggle 後自動補跑所有錯過的 run
> - **backfill**（手動）：自己指定時間範圍補跑，適合補特定時段的資料

之後每週一至五 18:00（台北時間）會自動執行。

### 手動補跑歷史資料（backfill）

如果需要補跑特定時間段的資料：

```bash
docker compose exec airflow-scheduler airflow dags backfill \
  -s 2026-01-01 \
  -e 2026-06-30 \
  taiwan_stock_daily_crawler_prod
```

> ⚠️ `-e` 是 exclusive，不包含結束日期。例如 `-e 2026-07-10` 只會跑到 7/9。
>
> ⚠️ `max_active_runs=1` 對 backfill 同樣有效，會一個 run 一個 run 依序執行。

### Service URLs（本機）

| 服務 | URL |
|---|---|
| FastAPI | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| 股價圖表 | http://localhost:8000/chart/{symbol} |
| Airflow UI | http://localhost:8080 |
| Flower | http://localhost:5555 |
| phpMyAdmin | http://localhost:8888 |

### 停止服務

```bash
docker compose down
```

## 部署到 GCP

使用 Terraform 一鍵部署到 Google Cloud Platform，密碼透過 GCP Secret Manager 安全管理。

### 前置條件

- [Terraform](https://developer.hashicorp.com/terraform/install)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install)
- GCP 帳號（[免費試用](https://cloud.google.com/free)）

### 部署步驟

**1. 登入 GCP 並設定 Project**

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

**2. 開啟需要的 API**

```bash
gcloud services enable \
  compute.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project YOUR_PROJECT_ID
```

**3. 建立 Terraform Service Account**

```bash
gcloud iam service-accounts create terraform-sa \
  --display-name "Terraform Service Account"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member "serviceAccount:terraform-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role "roles/editor"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member "serviceAccount:terraform-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role "roles/resourcemanager.projectIamAdmin"

gcloud iam service-accounts keys create ~/terraform-key.json \
  --iam-account terraform-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

**4. 建立 Secret Manager secrets**

```bash
echo -n "your_mysql_password" | gcloud secrets create mysql-password --data-file=- --project YOUR_PROJECT_ID
echo -n "your_mysql_root_password" | gcloud secrets create mysql-root-password --data-file=- --project YOUR_PROJECT_ID

# 產生 Fernet Key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
echo -n "your_fernet_key" | gcloud secrets create airflow-fernet-key --data-file=- --project YOUR_PROJECT_ID
echo -n "your_secret_key" | gcloud secrets create airflow-secret-key --data-file=- --project YOUR_PROJECT_ID
```

**5. 修改 Terraform 設定**

編輯 `terraform/variables.tf`：

```hcl
variable "project_id" {
  default = "your-gcp-project-id"
}
```

**6. 部署**

```bash
export GOOGLE_APPLICATION_CREDENTIALS=~/terraform-key.json
cd terraform
terraform init
terraform apply
```

### Terraform 建立的資源

| 資源 | 說明 |
|---|---|
| VPC + Subnet | 獨立的網路環境 |
| Firewall | 開放 8000、8080、5555、8888 port |
| Static IP | 固定的公開 IP |
| GCE VM（e2-standard-4） | 跑 docker-compose 的虛擬機 |
| Service Account | VM 用來讀取 Secret Manager 的身份 |
| IAM Binding | 授予 VM Secret Manager 讀取權限 |

VM 啟動後會自動從 Secret Manager 讀取密碼、clone repo 並執行 `docker-compose up -d`，約 5-10 分鐘後服務就緒。

### 關閉 VM（節省費用）

```bash
gcloud compute instances stop taiwan-stock-vm --zone asia-east1-b

# 需要時再開啟
gcloud compute instances start taiwan-stock-vm --zone asia-east1-b
```

### 刪除所有資源

```bash
terraform destroy
```

## API 說明

### GET /stock/{symbol}

查詢指定股票的歷史股價。

**參數：**
| 參數 | 類型 | 說明 |
|---|---|---|
| `symbol` | string | 股票代號（必填） |
| `start_date` | date | 起始日期（選填） |
| `end_date` | date | 結束日期（選填） |

**範例：**
```bash
# 查詢台積電所有資料
curl http://localhost:8000/stock/2330

# 查詢指定日期範圍
curl "http://localhost:8000/stock/2330?start_date=2026-07-01&end_date=2026-07-10"
```

**Response：**
```json
[
  {
    "symbol": "2330",
    "date": "2026-07-08",
    "open": 2445.0,
    "high": 2465.0,
    "low": 2428.0,
    "close": 2465.0,
    "volume": 25519000.0,
    "transaction": 94088.0,
    "trade_value": 62400000000.0
  }
]
```

### GET /chart/{symbol}

瀏覽器直接查看股價走勢圖（開盤價 + 收盤價折線圖）。

```
http://localhost:8000/chart/2330   # 台積電
http://localhost:8000/chart/2317   # 鴻海
http://localhost:8000/chart/2454   # 聯發科
```

### GET /health

```bash
curl http://localhost:8000/health
```

## 專案結構

```
taiwan_stock_crawler/
├── dags/
│   └── stock_crawler_dag.py     # Airflow DAG（每日爬蟲任務）
├── src/
│   ├── crawler/
│   │   └── twse_crawler.py      # TWSE 爬蟲（含 Pydantic schema 驗證）
│   ├── database/
│   │   └── db_manager.py        # MySQL Upsert + Redis Cache 封裝
│   └── api/
│       └── main.py              # FastAPI 查詢介面 + 股價圖表
├── tests/
│   └── test_crawler.py
├── terraform/
│   ├── main.tf                  # GCP 資源（VPC、VM、Firewall、Static IP、Service Account）
│   ├── variables.tf             # 變數設定（project_id、region 等）
│   ├── outputs.tf               # 輸出（VM IP、API URL）
│   └── startup.sh               # VM 啟動腳本（從 Secret Manager 讀取密碼）
├── Dockerfile                   # Airflow 服務（基於官方 apache/airflow:2.11.0）
├── Dockerfile.fastapi           # FastAPI 服務
├── docker-compose.yml
├── init.sql                     # MySQL 初始化（建立 DB、設定權限）
├── .env.example                 # 環境變數範本
├── requirements-airflow.txt     # Python 套件（Airflow 環境用）
└── .github/
    └── workflows/
        └── ci.yml               # GitHub Actions CI（pytest）
```

## 設計決策

**為什麼用 CeleryExecutor？**
台股資料有多個來源（上市、上櫃、期貨等），需要平行爬取多個 task，CeleryExecutor 支援水平擴展 worker 數量。相比 LocalExecutor 只能單機跑，CeleryExecutor 架構更接近生產環境。

**為什麼 Airflow metadata 和業務 DB 分開？**
混用同一個 DB 會讓 Airflow 的幾十張 metadata 表跟業務資料混在一起，維護困難。分開後 `taiwan_stock` DB 只有 `stock_prices` 一張表，清楚乾淨。

**為什麼用 Upsert 而不是 Insert？**
爬蟲可能因為網路問題重跑，`ON DUPLICATE KEY UPDATE` 確保重複爬取同一天的資料不會產生重複記錄。

**為什麼用 Redis 做 API Cache？**
股票歷史資料不會變動，適合 cache。TTL 設 1 小時，相同查詢第二次直接從 Redis 返回，不需要再查 MySQL。

**為什麼 Redis 同時當 Celery broker 和 API cache？**
兩者使用不同的 Redis DB（broker 用 DB 0，cache 用環境變數設定的 DB），互不干擾，省去多開一個 container 的成本。

**catchup=True 的設計考量**
設定 `catchup=True` 讓使用者可以自由指定 `start_date` 來決定要抓多久的歷史資料。搭配 `max_active_runs=1` 確保補跑時不會同時打多個 request 給證交所，避免被鎖 IP。

**為什麼用 Terraform 而不是直接 SSH 部署？**
Terraform 把基礎設施定義成 code，版本控制、可重現、一鍵部署。相比手動 SSH 設定，Terraform 讓任何人 clone repo 後都能用同樣的指令部署到自己的 GCP 帳號。

**為什麼用 GCP Secret Manager？**
密碼不應該寫在 GitHub 上，即使是 demo 專案。Secret Manager 讓 VM 在啟動時安全地讀取密碼，GitHub 上的 code 完全不含任何敏感資訊。