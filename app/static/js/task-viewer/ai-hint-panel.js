const ELIGIBLE_STATUSES = new Set([
    'WRONG_ANSWER', 'RUNTIME_ERROR', 'COMPILATION_ERROR',
    'TIME_LIMIT_EXCEEDED', 'MEMORY_LIMIT_EXCEEDED',
]);

export function createAIHintPanel({ fetcher, signal }) {
    const element = document.createElement('section');
    element.className = 'task-ai-hint';
    element.hidden = true;
    element.setAttribute('aria-label', 'AI-подсказка');
    const header = document.createElement('div');
    header.className = 'task-ai-hint__header';
    const title = document.createElement('strong');
    title.textContent = 'AI-помощь';
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'task-ai-hint__button';
    const quota = document.createElement('p');
    quota.className = 'task-ai-hint__quota';
    const modelLabel = document.createElement('label');
    modelLabel.className = 'task-ai-hint__model';
    const modelCaption = document.createElement('span');
    modelCaption.textContent = 'Модель для подсказки';
    const modelSelect = document.createElement('select');
    modelLabel.append(modelCaption, modelSelect);
    const message = document.createElement('p');
    message.className = 'task-ai-hint__message';
    message.setAttribute('role', 'status');
    message.setAttribute('aria-live', 'polite');
    header.append(title, button);
    element.append(header, quota, modelLabel, message);

    let submission = null;
    let availability = null;
    let statusLoading = false;
    let statusError = '';
    let hintError = '';
    let hintLoading = false;
    let submitting = false;
    let requestVersion = 0;
    let resetTimer = null;
    let selectedModel = '';
    signal.addEventListener('abort', () => window.clearTimeout(resetTimer), { once: true });

    const isEligible = () => ELIGIBLE_STATUSES.has(
        String(submission?.status || '').trim().toUpperCase().replace(/[\s-]+/g, '_')
    );
    const updateModels = () => {
        const models = availability?.models || [];
        if (!models.some(item => item.model === selectedModel)) {
            selectedModel = (models.find(item => item.remaining > 0) || models[0])?.model || '';
        }
        modelSelect.replaceChildren();
        for (const item of models) {
            const option = document.createElement('option');
            option.value = item.model;
            option.textContent = `${item.model} — осталось ${item.remaining} из ${item.daily_limit}`;
            option.disabled = item.remaining <= 0;
            modelSelect.append(option);
        }
        modelSelect.value = selectedModel;
    };
    modelSelect.addEventListener('change', () => {
        selectedModel = modelSelect.value;
        hintError = '';
        render();
    });
    const render = () => {
        element.hidden = !isEligible() || availability?.enabled === false || (!availability && !statusError);
        const cached = submission?.ai_hint;
        const chosen = availability?.models?.find(item => item.model === selectedModel);
        title.textContent = cached && submission.ai_hint_model ? `AI-помощь · ${submission.ai_hint_model}` : 'AI-помощь';
        modelLabel.hidden = Boolean(cached) || !availability?.models?.length;
        modelSelect.disabled = submitting || statusLoading || hintLoading;
        element.setAttribute('aria-busy', String(hintLoading || statusLoading));
        button.hidden = Boolean(cached) && !statusError;
        button.disabled = submitting || statusLoading || hintLoading || (!statusError && availability !== null && (
            availability.remaining <= 0 || !chosen || chosen.remaining <= 0
        ));
        button.textContent = hintLoading ? 'Готовим подсказку…' : statusLoading ? 'Проверяем доступ…' : statusError ? 'Повторить проверку доступа' : 'Подсказка';
        quota.textContent = availability
            ? `Осталось подсказок: ${availability.remaining} из ${availability.daily_limit}. Обновление в 00:00 по Москве.`
            : 'Лимиты обновляются в 00:00 по Москве.';
        message.classList.toggle('is-error', Boolean(statusError || hintError));
        message.setAttribute('role', statusError || hintError ? 'alert' : 'status');
        message.textContent = statusError || hintError || cached || (hintLoading
            ? 'AI анализирует отправленное решение. Обычно это занимает несколько секунд.'
            : availability?.remaining === 0
                ? 'Дневной лимит исчерпан. Новые подсказки будут доступны завтра.'
                : availability && !availability.models?.length
                    ? 'Доступные модели пока не настроены. Обратитесь к администратору.'
                    : chosen?.remaining === 0
                        ? 'Лимит выбранной модели исчерпан. Выберите другую модель.'
                : 'Подсказка к последнему отправленному решению поможет найти ошибку.');
    };
    const loadStatus = async () => {
        if (statusLoading || signal.aborted) return;
        statusLoading = true;
        statusError = '';
        render();
        try {
            const response = await fetcher('/api/submissions/ai-hints/status', { signal });
            if (!response.ok) throw new Error();
            const updated = await response.json();
            if (signal.aborted) return;
            if (availability?.remaining === 0 && updated.remaining > 0) hintError = '';
            availability = updated;
            updateModels();
            window.clearTimeout(resetTimer);
            resetTimer = window.setTimeout(() => void loadStatus(), Math.max(1000,
                new Date(availability.resets_at).getTime() - Date.now() + 1000));
        } catch (error) {
            if (!signal.aborted && error.message !== 'authentication-required') {
                statusError = 'Не удалось проверить доступ к AI-помощи. Повторите проверку.';
            }
        } finally {
            statusLoading = false;
            if (!signal.aborted) render();
        }
    };

    button.addEventListener('click', async () => {
        if (button.disabled || !isEligible() || signal.aborted) return;
        if (!availability || statusError) {
            await loadStatus();
            return;
        }
        // Refresh the quota after midnight and before every paid request.
        if (new Date(availability.resets_at).getTime() <= Date.now()) {
            await loadStatus();
            if (statusError || !availability.enabled || availability.remaining <= 0) return;
        }
        const target = submission;
        const model = selectedModel;
        const version = ++requestVersion;
        hintLoading = true;
        hintError = '';
        render();
        try {
            const response = await fetcher(`/api/submissions/${encodeURIComponent(target.id)}/hint`, {
                method: 'POST', signal,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model }),
            });
            const data = await response.json().catch(() => ({}));
            if (signal.aborted || version !== requestVersion) return;
            if (!response.ok) {
                if (response.status === 403) availability.enabled = false;
                if ([422, 429].includes(response.status)) await loadStatus();
                throw new Error(typeof data.detail === 'string' ? data.detail : 'Сервис AI временно недоступен. Попробуйте позже.');
            }
            availability = data;
            updateModels();
            target.ai_hint = data.hint;
            target.ai_hint_model = data.model;
        } catch (error) {
            if (!signal.aborted && version === requestVersion && error.message !== 'authentication-required') {
                hintError = error instanceof TypeError
                    ? 'Не удалось получить подсказку. Проверьте подключение и попробуйте снова.'
                    : error.message || 'Не удалось получить подсказку. Попробуйте позже.';
            }
        } finally {
            if (!signal.aborted && version === requestVersion) {
                hintLoading = false;
                render();
            }
        }
    });

    return {
        element,
        render(nextSubmission) {
            const changed = submission?.id !== nextSubmission?.id;
            if (changed) {
                requestVersion += 1;
                hintLoading = false;
                hintError = '';
            } else if (submission?.ai_hint && nextSubmission) {
                nextSubmission.ai_hint ||= submission.ai_hint;
                nextSubmission.ai_hint_model ||= submission.ai_hint_model;
            }
            submission = nextSubmission;
            render();
            if (isEligible() && (changed || !availability)) void loadStatus();
        },
        setBusy(value) { submitting = value; render(); },
    };
}
