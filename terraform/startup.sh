#!/bin/bash
apt-get update
apt-get install -y docker.io docker-compose git

systemctl start docker
systemctl enable docker

git clone ${repo_url} /app
cd /app

# Read secrets from GCP Secret Manager
MYSQL_PASSWORD=$(gcloud secrets versions access latest --secret="mysql-password" --project taiwan-stock-crawler-502102)
MYSQL_ROOT_PASSWORD=$(gcloud secrets versions access latest --secret="mysql-root-password" --project taiwan-stock-crawler-502102)
AIRFLOW_FERNET_KEY=$(gcloud secrets versions access latest --secret="airflow-fernet-key" --project taiwan-stock-crawler-502102)
AIRFLOW_WEBSERVER_SECRET_KEY=$(gcloud secrets versions access latest --secret="airflow-secret-key" --project taiwan-stock-crawler-502102)

# Create .env from secrets
cat > .env << EOF
MYSQL_USER=airflow_user
MYSQL_ROOT_PASSWORD=$${MYSQL_ROOT_PASSWORD}
MYSQL_PASSWORD=$${MYSQL_PASSWORD}
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DB=taiwan_stock
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
AIRFLOW_FERNET_KEY=$${AIRFLOW_FERNET_KEY}
AIRFLOW_WEBSERVER_SECRET_KEY=$${AIRFLOW_WEBSERVER_SECRET_KEY}
API_PORT=8000
EOF

docker-compose up -d