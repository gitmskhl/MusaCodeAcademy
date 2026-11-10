#!/usr/bin/env bash
# Run on the host, not inside a container. Requires the project's Docker Compose.
set -Eeuo pipefail
umask 077

usage() {
    cat <<'HELP'
Использование: ./scripts/restore-server.sh [--yes] /путь/backup.dump

Полностью заменяет БД этого Docker Compose. Создаёт резервную копию в backups/.
При ошибке пытается вернуть прежнюю базу. Код и uploads не переносит.
Принимает только доверенные полные архивы pg_dump custom (.dump).
--yes: не запрашивать подтверждение полной замены.
HELP
}

confirm=1
if [[ ${1:-} == --help || ${1:-} == -h ]]; then usage; exit 0; fi
if [[ ${1:-} == --yes ]]; then confirm=0; shift; fi
if [[ $# != 1 ]]; then usage >&2; exit 2; fi
source_dump=$(realpath -- "$1")
[[ -f "$source_dump" && -r "$source_dump" && -s "$source_dump" ]] || { echo 'Файл копии не найден, пуст или недоступен.' >&2; exit 2; }
[[ $(head -c 5 -- "$source_dump") == PGDMP ]] || { echo 'Нужен архив pg_dump в custom-формате (.dump).' >&2; exit 2; }

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$project_dir"
command -v flock >/dev/null || { echo 'Требуется flock (пакет util-linux).' >&2; exit 2; }
exec 9> .restore-server.lock
flock -n 9 || { echo 'Другое восстановление уже выполняется.' >&2; exit 1; }
compose=(docker compose)
"${compose[@]}" version >/dev/null

# Read only the database name, never source .env as shell code or print passwords.
database=$("${compose[@]}" exec -T postgres sh -eu -c 'printf "%s" "$POSTGRES_DB"')
[[ -n "$database" && "$database" != postgres && "$database" != template* ]] || { echo 'Недопустимое имя целевой БД.' >&2; exit 1; }
[[ $("${compose[@]}" exec -T redis redis-cli ping) == PONG ]] || { echo 'Redis недоступен.' >&2; exit 1; }

stamp=$(date -u +%Y%m%dT%H%M%SZ)
candidate="mca_restore_${stamp}_$$"
previous="mca_previous_${stamp}_$$"
mkdir -p backups
chmod 700 backups
run_dir=$(mktemp -d "$project_dir/backups/restore_${stamp}_XXXXXX")
backup_file="$run_dir/before.dump"
log_file="$run_dir/restore.log"
touch "$log_file"
original_services=()
running=$("${compose[@]}" ps --status running --services)
for service in app worker; do
    if [[ $'\n'"$running"$'\n' == *$'\n'"$service"$'\n'* ]]; then original_services+=("$service"); fi
done
candidate_created=0
stopped=0
switched=0

drop_database() {
    "${compose[@]}" exec -T postgres sh -eu -c \
        'exec dropdb --no-password --username "$POSTGRES_USER" --maintenance-db=postgres --if-exists --force -- "$1"' sh "$1"
}

# Both renames commit together. The previous database remains intact for rollback.
switch_database() {
    "${compose[@]}" exec -T postgres sh -eu -c \
        'exec psql -X --no-password --username "$POSTGRES_USER" --dbname postgres -v ON_ERROR_STOP=1 -v live="$POSTGRES_DB" -v incoming="$1" -v outgoing="$2"' sh "$1" "$2" <<'SQL'
BEGIN;
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE datname IN (:'live', :'incoming') AND pid <> pg_backend_pid();
SELECT format('ALTER DATABASE %I RENAME TO %I', :'live', :'outgoing') \gexec
SELECT format('ALTER DATABASE %I RENAME TO %I', :'incoming', :'live') \gexec
COMMIT;
SQL
}

rebuild_queue() {
    "${compose[@]}" run --rm --no-deps -T app python -m app.cli.database_restore rebuild-queue
}

start_services() {
    "${compose[@]}" up -d --no-deps --wait --wait-timeout 90 app || return 1
    "${compose[@]}" up -d --no-deps --wait --wait-timeout 30 worker || return 1
}

finish() {
    result=$?
    trap - EXIT INT TERM
    if (( result != 0 )); then
        echo "Восстановление не завершено. Подробности: $log_file" >&2
        rollback_ok=1
        if (( switched )); then
            echo 'Возвращаем прежнюю базу…' >&2
            # Stop even partially started services before touching names or Redis.
            if ! "${compose[@]}" stop -t 30 app worker >>"$log_file" 2>&1; then rollback_ok=0; fi
            if (( rollback_ok )); then
                if switch_database "$previous" "$candidate" >>"$log_file" 2>&1; then
                    switched=0
                    candidate_created=1
                else
                    rollback_ok=0
                fi
            fi
        fi
        if (( stopped && rollback_ok )); then
            if ! rebuild_queue >>"$log_file" 2>&1; then rollback_ok=0; fi
            if (( rollback_ok && ${#original_services[@]} )); then
                if ! "${compose[@]}" up -d --no-deps --wait --wait-timeout 90 "${original_services[@]}" >>"$log_file" 2>&1; then rollback_ok=0; fi
            fi
        fi
        if (( ! rollback_ok )); then
            "${compose[@]}" stop -t 30 app worker >>"$log_file" 2>&1 || true
            echo "Автоматический откат не завершён. Сервисы оставлены остановленными. Копия: $backup_file; прежняя БД может называться $previous." >&2
        elif (( stopped )); then
            echo 'Прежняя база возвращена; исходное состояние сервисов восстановлено.' >&2
        fi
    fi
    if (( candidate_created )); then
        drop_database "$candidate" >>"$log_file" 2>&1 || echo "Не удалось удалить временную БД $candidate. См. журнал." >&2
    fi
    exit "$result"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "Целевая база: $database"
echo 'Она будет полностью заменена. Записи, появившиеся после экспорта, исчезнут.'
echo 'Загруженные изображения (uploads) и код этим скриптом не изменяются.'
if (( confirm )); then
    read -r -p 'Для продолжения введите RESTORE: ' answer
    [[ "$answer" == RESTORE ]] || { echo 'Отменено.'; exit 0; }
fi

echo 'Проверяем архив и восстанавливаем во временную базу…'
"${compose[@]}" exec -T postgres pg_restore --list < "$source_dump" >>"$log_file" 2>&1
"${compose[@]}" exec -T postgres sh -eu -c \
    'exec createdb --no-password --username "$POSTGRES_USER" --maintenance-db=postgres --template=template0 -- "$1"' sh "$candidate" >>"$log_file" 2>&1
candidate_created=1
"${compose[@]}" exec -T postgres sh -eu -c \
    'exec pg_restore --no-password --username "$POSTGRES_USER" --dbname "$1" --no-owner --no-privileges --exit-on-error --single-transaction' sh "$candidate" < "$source_dump" >>"$log_file" 2>&1
"${compose[@]}" run --rm --no-deps -T app python -m app.cli.database_restore prepare "$candidate" >>"$log_file" 2>&1

echo 'Архив проверен. Останавливаем сайт и worker, сохраняем текущую базу…'
stopped=1
"${compose[@]}" stop -t 30 app worker >>"$log_file" 2>&1
"${compose[@]}" exec -T postgres sh -eu -c \
    'exec pg_dump --no-password --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --format=custom --no-owner --no-privileges' > "$backup_file" 2>>"$log_file"
[[ -s "$backup_file" ]]
"${compose[@]}" exec -T postgres pg_restore --list < "$backup_file" >>"$log_file" 2>&1

echo 'Переключаем базу, восстанавливаем очередь проверок и запускаем сервисы…'
# Do not interrupt the short name swap between COMMIT and recording its state.
trap '' INT TERM
switch_database "$candidate" "$previous" >>"$log_file" 2>&1
switched=1
candidate_created=0
trap 'exit 130' INT
trap 'exit 143' TERM
rebuild_queue >>"$log_file" 2>&1
start_services >>"$log_file" 2>&1

# The file backup is retained; remove the redundant old database only after health checks.
switched=0
stopped=0
if ! drop_database "$previous" >>"$log_file" 2>&1; then
    echo "Сайт запущен, но прежнюю БД $previous нужно удалить вручную. См. журнал." >&2
fi
echo "Готово. Сайт и worker запущены. Резервная копия прежней БД: $backup_file"
echo "Журнал: $log_file"
