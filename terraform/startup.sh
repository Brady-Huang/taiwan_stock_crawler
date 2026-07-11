#!/bin/bash
apt-get update
apt-get install -y docker.io docker-compose git

systemctl start docker
systemctl enable docker

git clone ${repo_url} /app
cd /app

# Copy example env file for demo purposes.
# For production, replace .env with your own configuration before running docker-compose.
cp .env.example .env

docker-compose up -d