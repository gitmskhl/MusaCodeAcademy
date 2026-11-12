#!/usr/bin/env bash
set -euo pipefail

# Проверяем операционную систему
source /etc/os-release

if [[ "$ID" != "ubuntu" ]]; then
    echo "Ошибка: скрипт предназначен для Ubuntu."
    exit 1
fi

# Проверяем, что Docker ещё не установлен
if command -v docker >/dev/null 2>&1; then
    echo "Docker уже установлен."
    docker --version
    echo "Проверь Docker Compose:"
    docker compose version || true
    exit 0
fi

echo "=== Обновление списка пакетов ==="
sudo apt-get update

echo "=== Установка зависимостей ==="
sudo apt-get install -y ca-certificates curl

echo "=== Добавление GPG-ключа Docker ==="
sudo install -m 0755 -d /etc/apt/keyrings

sudo curl -fsSL \
    https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc

sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "=== Добавление репозитория Docker ==="
sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

echo "=== Установка Docker ==="
sudo apt-get update

sudo apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

echo "=== Запуск Docker ==="
sudo systemctl enable --now docker

echo "=== Проверка версий ==="
sudo docker --version
sudo docker compose version

echo "=== Тестовый контейнер ==="
sudo docker run --rm hello-world

echo "=== Docker успешно установлен! ==="
