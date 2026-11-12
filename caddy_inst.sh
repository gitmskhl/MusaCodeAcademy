sudo bash <<'SCRIPT'
set -euo pipefail

# Проверяем порт до установки.
if command -v ss >/dev/null 2>&1; then
    listeners=$(ss -H -ltnp 'sport = :80')
    if [[ -n "$listeners" ]]; then
        echo "Порт 80 уже занят:"
        echo "$listeners"
        echo "Освободите его и повторите запуск скрипта."
        exit 1
    fi
fi

echo "Устанавливаем зависимости..."
apt-get update
apt-get install -y \
    debian-keyring debian-archive-keyring \
    apt-transport-https ca-certificates curl gnupg

temp_dir=$(mktemp -d)
trap 'rm -rf "$temp_dir"' EXIT

echo "Добавляем официальный репозиторий Caddy..."
curl -fsSL \
    https://dl.cloudsmith.io/public/caddy/stable/gpg.key \
    -o "$temp_dir/caddy.key"

gpg --batch --yes --dearmor \
    --output "$temp_dir/caddy.gpg" "$temp_dir/caddy.key"

install -m 0644 "$temp_dir/caddy.gpg" \
    /usr/share/keyrings/caddy-stable-archive-keyring.gpg

curl -fsSL \
    https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt \
    -o "$temp_dir/caddy-stable.list"

install -m 0644 "$temp_dir/caddy-stable.list" \
    /etc/apt/sources.list.d/caddy-stable.list

apt-get update
apt-get install -y caddy

echo "Настраиваем HTTP-прокси..."
if [[ -f /etc/caddy/Caddyfile ]]; then
    backup_file=$(mktemp /etc/caddy/Caddyfile.backup.XXXXXX)
    cp -p /etc/caddy/Caddyfile "$backup_file"
    echo "Прежняя конфигурация сохранена: $backup_file"
fi

cat > /etc/caddy/Caddyfile <<'CADDY'
:80 {
    encode zstd gzip
    reverse_proxy 127.0.0.1:8000
}
CADDY

chmod 0644 /etc/caddy/Caddyfile
caddy fmt --overwrite /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

if command -v ufw >/dev/null 2>&1; then
    if LC_ALL=C ufw status | grep -q '^Status: active'; then
        ufw allow 80/tcp
    fi
fi

systemctl enable --now caddy
systemctl reload caddy
systemctl is-active --quiet caddy

echo
echo "Caddy установлен и работает."
echo "Откройте в браузере: http://IP_ВАШЕГО_VPS"
echo "Если у провайдера включён firewall, разрешите входящий TCP-порт 80."

if curl -fsS --max-time 10 \
    http://127.0.0.1/openapi.json >/dev/null; then
    echo "Проверка приложения через Caddy: успешно."
else
    echo "Приложение пока не отвечает успешно через Caddy."
    echo "Проверьте запуск app и журнал:"
    echo "sudo journalctl -u caddy -n 50 --no-pager"
fi
SCRIP
