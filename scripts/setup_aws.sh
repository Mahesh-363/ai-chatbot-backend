#!/bin/bash
# Quick EC2 setup script (Amazon Linux 2023 / Ubuntu 22.04)
set -e

echo "==> Installing Docker..."
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

echo "==> Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

echo "==> Cloning repo..."
# git clone https://github.com/YOUR_USERNAME/ai-chatbot.git
# cd ai-chatbot

echo "==> Copying .env..."
cp .env.example .env
# Edit .env with production values

echo "==> Building and starting services..."
docker-compose -f docker-compose.yml up --build -d

echo "==> Creating superuser..."
docker-compose exec api python manage.py createsuperuser

echo "==> Done! API running on http://$(curl -s ifconfig.me)"
