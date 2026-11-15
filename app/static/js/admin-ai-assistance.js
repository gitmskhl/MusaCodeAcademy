export function createAIAssistanceSettings({ user, api, onSaved }) {
    const node = (tag, text, className) => {
        const element = document.createElement(tag);
        if (text !== undefined) element.textContent = text;
        if (className) element.className = className;
        return element;
    };
    const element = node('div');
    const toggle = node('input');
    toggle.type = 'checkbox';
    toggle.checked = user.ai_assistance_enabled;
    const caption = node('label', undefined, 'monitoring-ai-toggle');
    caption.append(toggle, document.createTextNode('Разрешить AI-подсказки для этого пользователя'));
    const form = node('form', undefined, 'monitoring-ai-settings');
    form.hidden = !toggle.checked;
    const dailyLabel = node('label', 'Всего запросов в день', 'field');
    const daily = node('input');
    daily.type = 'number';
    daily.min = '1';
    daily.max = '1000';
    daily.step = '1';
    daily.required = true;
    daily.value = user.ai_daily_limit;
    dailyLabel.append(daily);
    const rowsHost = node('div', undefined, 'monitoring-ai-models');
    const add = node('button', 'Добавить модель', 'button button--ghost');
    add.type = 'button';
    const total = node('p', '', 'monitoring-muted');
    const save = node('button', 'Сохранить настройки', 'button button--primary');
    save.type = 'submit';
    const error = node('p', '', 'monitoring-ai-error');
    error.setAttribute('role', 'alert');
    error.hidden = true;
    const retry = node('button', 'Повторить загрузку моделей', 'button button--ghost');
    retry.type = 'button';
    retry.hidden = true;
    form.append(dailyLabel, node('p', 'Выберите модели и распределите между ними все дневные запросы. Лимиты обновляются в 00:00 по Москве.', 'monitoring-muted'), rowsHost, add, total, save);
    element.append(caption, form, error, retry);

    let models = [];
    const rows = [];
    let saving = false;
    let loading = false;
    const showError = (message = '') => { error.textContent = message; error.hidden = !message; };
    const sync = () => {
        const allocated = rows.reduce((sum, row) => sum + (Number(row.count.value) || 0), 0);
        total.textContent = `Распределено запросов: ${allocated} из ${daily.value || 0}. Сумма должна совпадать с общим лимитом.`;
        total.classList.toggle('monitoring-ai-error', allocated !== Number(daily.value));
        form.hidden = !toggle.checked;
        toggle.disabled = saving;
        for (const control of form.querySelectorAll('input, select, button')) control.disabled = saving || loading;
        add.disabled ||= !models.some(model => !rows.some(row => row.select.value === model));
        save.disabled ||= models.length === 0;
        save.textContent = saving ? 'Сохраняем…' : 'Сохранить настройки';
    };
    const addRow = (model, limit = 1) => {
        const wrapper = node('div', undefined, 'monitoring-ai-model-row');
        const modelLabel = node('label', 'Модель', 'field');
        const select = node('select');
        const choices = models.includes(model) ? models : [model, ...models];
        for (const value of choices) {
            const option = node('option', models.includes(value) ? value : `${value} (нет в .env)`);
            option.value = value;
            select.append(option);
        }
        select.value = model;
        modelLabel.append(select);
        const limitLabel = node('label', 'Запросов в день', 'field');
        const count = node('input');
        count.type = 'number';
        count.min = '1';
        count.max = '1000';
        count.step = '1';
        count.required = true;
        count.value = limit;
        limitLabel.append(count);
        const remove = node('button', 'Удалить', 'button button--ghost');
        remove.type = 'button';
        remove.setAttribute('aria-label', `Удалить правило для ${model}`);
        const row = { select, count, wrapper };
        remove.addEventListener('click', () => { rows.splice(rows.indexOf(row), 1); wrapper.remove(); sync(); });
        select.addEventListener('change', sync);
        count.addEventListener('input', sync);
        wrapper.append(modelLabel, limitLabel, remove);
        rows.push(row);
        rowsHost.append(wrapper);
        sync();
    };
    const loadModels = async () => {
        loading = true;
        retry.hidden = true;
        showError();
        sync();
        try {
            models = await api('/api/admin/ai-models');
            if (!models.length) showError('Модели не настроены. Добавьте AI_MODEL_1, AI_MODEL_2 и другие модели в .env и перезапустите приложение.');
            rows.length = 0;
            rowsHost.replaceChildren();
            const allocations = user.ai_model_limits ?? (models.length ? { [models[0]]: user.ai_daily_limit } : {});
            for (const [model, limit] of Object.entries(allocations)) addRow(model, limit);
        } catch (failure) {
            showError(failure.message || 'Не удалось загрузить модели.');
            retry.hidden = false;
        } finally {
            loading = false;
            sync();
        }
    };
    toggle.addEventListener('change', async () => {
        if (saving) return;
        saving = true;
        showError();
        sync();
        try {
            const updated = await api(`/api/admin/users/${user.id}/ai-assistance`, {
                method: 'PATCH', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: toggle.checked }),
            });
            Object.assign(user, updated);
            onSaved?.(toggle.checked ? 'AI-помощь включена.' : 'AI-помощь выключена.');
        } catch (failure) {
            toggle.checked = user.ai_assistance_enabled;
            showError(failure.message);
        } finally {
            saving = false;
            sync();
        }
    });
    daily.addEventListener('input', sync);
    add.addEventListener('click', () => {
        const next = models.find(model => !rows.some(row => row.select.value === model));
        if (next) addRow(next);
    });
    retry.addEventListener('click', () => void loadModels());
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (saving || loading || !form.reportValidity()) return;
        showError();
        const allocations = {};
        for (const row of rows) {
            if (Object.hasOwn(allocations, row.select.value)) { showError('Каждую модель можно выбрать только один раз.'); return; }
            allocations[row.select.value] = Number(row.count.value);
        }
        if (!rows.length || Object.values(allocations).reduce((sum, value) => sum + value, 0) !== Number(daily.value)) {
            showError('Сумма запросов по моделям должна совпадать с дневным лимитом.');
            return;
        }
        saving = true;
        sync();
        try {
            const updated = await api(`/api/admin/users/${user.id}/ai-assistance`, {
                method: 'PATCH', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: toggle.checked, daily_limit: Number(daily.value), model_limits: allocations }),
            });
            Object.assign(user, updated);
            onSaved?.('Настройки AI-помощи сохранены.');
        } catch (failure) {
            showError(failure.message || 'Не удалось сохранить настройки.');
        } finally {
            saving = false;
            sync();
        }
    });
    void loadModels();
    return element;
}
