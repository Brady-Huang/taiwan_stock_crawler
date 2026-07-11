CREATE DATABASE IF NOT EXISTS airflow_metadata;
CREATE DATABASE IF NOT EXISTS taiwan_stock;

CREATE USER IF NOT EXISTS 'airflow_user'@'%' IDENTIFIED BY 'demo1234';
GRANT ALL PRIVILEGES ON taiwan_stock.* TO 'airflow_user'@'%';
GRANT ALL PRIVILEGES ON airflow_metadata.* TO 'airflow_user'@'%';

FLUSH PRIVILEGES;
