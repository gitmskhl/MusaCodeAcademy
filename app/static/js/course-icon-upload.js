const MAX_ICON_SIZE = 10 * 1024 * 1024;
const ICON_TYPES = new Set(['image/png', 'image/jpeg', 'image/webp', 'image/gif']);

export function initCourseIconUpload(form, initialUrl = null) {
    const input = form.querySelector('#course-icon');
    const preview = form.querySelector('[data-course-icon-preview]');
    const image = form.querySelector('[data-course-icon-image]');
    const remove = form.querySelector('[data-course-icon-remove]');
    const error = form.querySelector('[data-error-for="icon"]');
    let iconUrl = initialUrl;
    let objectUrl = null;

    const showError = (message = '') => {
        error.textContent = message;
        if (message) input.setAttribute('aria-invalid', 'true');
        else input.removeAttribute('aria-invalid');
    };

    const validate = () => {
        const file = input.files[0];
        if (!file) return '';
        if (!ICON_TYPES.has(file.type) || !/\.(png|jpe?g|webp|gif)$/i.test(file.name)) {
            return 'Выберите изображение PNG, JPEG, WebP или GIF.';
        }
        if (!file.size) return 'Выбранный файл пуст.';
        if (file.size > MAX_ICON_SIZE) return 'Размер иконки не должен превышать 10 МБ.';
        return '';
    };

    const render = () => {
        if (objectUrl) URL.revokeObjectURL(objectUrl);
        objectUrl = null;
        const file = input.files[0];
        if (file && !validate()) objectUrl = URL.createObjectURL(file);
        const source = objectUrl || iconUrl;
        preview.hidden = !source;
        remove.hidden = !source && !file;
        if (source) image.src = source;
        else image.removeAttribute('src');
    };

    input.addEventListener('change', () => {
        showError(validate());
        render();
    });
    remove.addEventListener('click', () => {
        input.value = '';
        iconUrl = null;
        showError();
        render();
    });
    window.addEventListener('pagehide', () => {
        if (objectUrl) URL.revokeObjectURL(objectUrl);
    });
    render();

    return {
        setBusy(busy) {
            input.disabled = busy;
            remove.disabled = busy;
        },
        async upload(token) {
            const validationError = validate();
            if (validationError) {
                showError(validationError);
                input.focus();
                throw new Error(validationError);
            }
            const file = input.files[0];
            if (!file) return iconUrl;

            showError();
            try {
                const body = new FormData();
                body.append('file', file);
                const response = await fetch('/api/files/images', {
                    method: 'POST',
                    headers: { Authorization: `Bearer ${token}` },
                    body,
                });
                if (!response.ok) {
                    if (response.status === 401) {
                        throw new Error('Сессия истекла. Войдите заново.');
                    }
                    if (response.status === 413) {
                        throw new Error('Размер иконки не должен превышать 10 МБ.');
                    }
                    throw new Error('Не удалось загрузить иконку. Проверьте файл и попробуйте ещё раз.');
                }
                const uploaded = await response.json();
                if (!/^images\/[a-zA-Z0-9_-]+\.(png|jpe?g|webp|gif)$/.test(uploaded.storage_path)) {
                    throw new Error('Сервер вернул некорректный адрес иконки.');
                }
                iconUrl = `/uploads/${uploaded.storage_path}`;
                input.value = '';
                render();
                return iconUrl;
            } catch (err) {
                const message = err instanceof TypeError
                    ? 'Не удалось загрузить иконку. Проверьте соединение и попробуйте ещё раз.'
                    : err.message;
                showError(message);
                throw new Error(message);
            }
        },
    };
}
