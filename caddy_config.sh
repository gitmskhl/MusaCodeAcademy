sudo bash <<'SCRIPT'
set -euo pipefail

command -v caddy >/dev/null || {
    echo "Caddy не установлен."
    exit 1
}

config=/etc/caddy/Caddyfile
backup="${config}.bak.$(date +%Y%m%d-%H%M%S)"
candidate=$(mktemp /etc/caddy/Caddyfile.XXXXXX)
trap 'rm -f "$candidate"' EXIT

cat > "$candidate" <<'EOF'
mcodeacademy.ru {
    encode zstd gzip
    reverse_proxy 127.0.0.1:8000
}
EOF

echo "Проверяем конфигурацию…"
caddy validate --config "$candidate" --adapter caddyfile

cp -p "$config" "$backup"
install -m 644 "$candidate" "$config"

echo "Применяем настройки…"
if systemctl is-active --quiet caddy; then
    if ! systemctl reload caddy; then
        cp -p "$backup" "$config"
        systemctl reload caddy || true
        echo "Ошибка применения. Прежняя конфигурация возвращена."
        exit 1
    fi
else
    if ! systemctl start caddy; then
        cp -p "$backup" "$config"
        echo "Ошибка запуска. Прежний файл конфигурации возвращён."
        journalctl -u caddy -n 30 --no-pager
        exit 1
    fi
fi

systemctl enable caddy

echo "Конфигурация применена: https://mcodeacademy.ru"
echo "Копия прежней конфигурации: $backup"
echo "Свежий журнал:"
journalctl -u caddy -n 20 --no-pager
SCRIPT
