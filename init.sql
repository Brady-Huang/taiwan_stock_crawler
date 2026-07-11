CREATE DATABASE IF NOT EXISTS airflow_metadata;
CREATE DATABASE IF NOT EXISTS taiwan_stock;

GRANT ALL PRIVILEGES ON airflow_metadata.* TO 'airflow_user'@'%';

FLUSH PRIVILEGES;