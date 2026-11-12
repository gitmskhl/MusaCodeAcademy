bash <<'SCRIPT'
set -euo pipefail

[[ -f .env ]] || {
    echo "Ошибка: перейди в папку проекта, где находится .env."
    exit 1
}

backup=".env.bak.$(date +%Y%m%d-%H%M%S)"
cp -p .env "$backup"
chmod 600 "$backup"

# Uvicorn будет учитывать HTTPS-заголовки от Caddy.
sed -i '/^[[:space:]]*\(export[[:space:]]\+\)\?FORWARDED_ALLOW_IPS[[:space:]]*=/d' .env
printf '\nFORWARDED_ALLOW_IPS=*\n' >> .env

echo "Перезапускаем приложение с новой настройкой…"
docker compose up -d --no-deps --force-recreate \
    --wait --wait-timeout 120 app

echo "Проверяем ссылку на CSS…"
curl --fail --silent --show-error --max-time 20 \
    https://mcodeacademy.ru/ |
    grep -oE '<link[^>]*href="[^"]*home\.css[^"]*"[^>]*>'

echo "Ожидается ссылка https://mcodeacademy.ru/static/css/home.css"
echo "Копия настроек: $backup"
echo "Обнови страницу через Ctrl+Shift+R."
SCRIPT
