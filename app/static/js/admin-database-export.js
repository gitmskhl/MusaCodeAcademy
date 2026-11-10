export function initDatabaseExport() {
    const button = document.querySelector('[data-database-export]');
    const status = document.querySelector('[data-database-export-status]');
    if (!button || !status) return;

    button.addEventListener('click', async () => {
        if (button.disabled) return;
        button.disabled = true;
        button.textContent = 'Подготовка копии…';
        status.textContent = 'Создаём и скачиваем резервную копию. Дождитесь завершения.';
        let objectUrl;
        try {
            const response = await fetch('/api/admin/database/export', {
                method: 'POST',
                headers: { Authorization: `Bearer ${localStorage.getItem('musa_code_academy_token') || ''}` },
                cache: 'no-store',
            });
            if (!response.ok) {
                const data = await response.json().catch(() => null);
                throw new Error(typeof data?.detail === 'string' ? data.detail : 'Не удалось экспортировать БД. Проверьте права доступа и попробуйте снова.');
            }
            const blob = await response.blob();
            const disposition = response.headers.get('Content-Disposition') || '';
            const filename = disposition.match(/filename="?([a-zA-Z0-9_.-]+\.dump)"?/)?.[1]
                || 'musacodeacademy.dump';
            objectUrl = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = objectUrl;
            link.download = filename;
            document.body.append(link);
            link.click();
            link.remove();
            status.textContent = 'Копия передана браузеру для сохранения. Файл содержит персональные данные — храните его в надёжном месте.';
        } catch (error) {
            status.textContent = error instanceof Error ? error.message : 'Не удалось экспортировать БД.';
        } finally {
            if (objectUrl) window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
            button.disabled = false;
            button.textContent = 'Экспорт БД';
        }
    });
}
