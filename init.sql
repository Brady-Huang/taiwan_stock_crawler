-- 確保資料庫存在
CREATE DATABASE IF NOT EXISTS airflow_metadata;
CREATE DATABASE IF NOT EXISTS taiwan_stock;

-- 強制 root 使用傳統密碼驗證，確保 pymysql 驅動 100% 能連上
ALTER USER 'root'@'%' IDENTIFIED WITH mysql_native_password BY 'test';

-- 建立 user 帳號作為備援
CREATE USER IF NOT EXISTS 'user'@'%' IDENTIFIED BY 'test';
GRANT ALL PRIVILEGES ON taiwan_stock.* TO 'user'@'%';

FLUSH PRIVILEGES;