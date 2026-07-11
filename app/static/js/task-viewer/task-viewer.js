import { createCodeEditorView } from '../step-renderer/codemirror/code-editor-view.js';
import { authFetch } from '../course-auth.js';

const SUBMIT_LABEL = 'Отправить решение';
const SUBMITTING_LABEL = 'Отправляем решение...';

const createMetaItem = (icon, label, value) => {
    const item = document.createElement('span');
    item.className = 'task-viewer__meta-item';
    item.textContent = `${icon} ${label}: ${value}`;
    return item;
};

const createDivider = () => {
    const divider = document.createElement('div');
    divider.className = 'task-viewer__divider';
    divider.setAttribute('aria-hidden', 'true');
    return divider;
};

const createSubmitButton = () => {
    const button = document.createElement('button');
    button.className = 'task-viewer__submit';
    button.type = 'button';
    button.textContent = SUBMIT_LABEL;
    return button;
};

const getErrorDetail = async (response) => {
    try {
        const body = await response.json();
        return typeof body.detail === 'string' && body.detail.trim()
            ? body.detail
            : null;
    } catch {
        return null;
    }
};

export const clearTaskViewer = (container) => {
    container.replaceChildren();
    container.hidden = true;
};

export const renderTaskError = (container, message) => {
    const card = document.createElement('article');
    card.className = 'task-viewer__card task-viewer__card--error';
    card.setAttribute('role', 'alert');
    card.textContent = message;

    container.replaceChildren(card);
    container.hidden = false;
};

export const renderTaskViewer = (container, task) => {
    let sourceCode = task.starter_code || '';

    const card = document.createElement('article');
    card.className = 'task-viewer__card';

    const header = document.createElement('header');
    header.className = 'task-viewer__header';

    const title = document.createElement('h2');
    title.className = 'task-viewer__title';
    title.textContent = 'Практическое задание';

    const meta = document.createElement('div');
    meta.className = 'task-viewer__meta';
    meta.append(
        createMetaItem('⏱', 'Время', `${task.time_limit_ms} мс`),
        createMetaItem('💾', 'Память', `${task.memory_limit_mb} МБ`)
    );

    header.append(title, meta);

    const editorHost = document.createElement('div');
    editorHost.className = 'task-viewer__code-editor';

    const actions = document.createElement('div');
    actions.className = 'task-viewer__actions';

    const submitStatus = document.createElement('p');
    submitStatus.className = 'task-viewer__submit-status';
    submitStatus.setAttribute('role', 'status');
    submitStatus.setAttribute('aria-live', 'polite');

    const submitButton = createSubmitButton();
    let isSubmitting = false;

    submitButton.addEventListener('click', async () => {
        if (isSubmitting) {
            return;
        }

        if (!sourceCode.trim()) {
            submitStatus.textContent = 'Введите код решения.';
            submitStatus.classList.add('is-error');
            return;
        }

        isSubmitting = true;
        submitButton.disabled = true;
        submitButton.textContent = SUBMITTING_LABEL;
        submitStatus.textContent = '';
        submitStatus.classList.remove('is-error');

        try {
            const response = await authFetch('/api/submissions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    task_id: task.id,
                    source_code: sourceCode,
                }),
            });

            if (!response.ok) {
                const detail = await getErrorDetail(response);
                throw new Error(detail || 'Не удалось отправить решение.');
            }

            submitStatus.textContent = 'Решение отправлено и ожидает проверки.';
        } catch (error) {
            if (error.message !== 'authentication-required') {
                submitStatus.textContent = error.message || 'Не удалось отправить решение.';
                submitStatus.classList.add('is-error');
            }
        } finally {
            isSubmitting = false;
            submitButton.disabled = false;
            submitButton.textContent = SUBMIT_LABEL;
        }
    });

    actions.append(submitStatus, submitButton);
    card.append(header, createDivider(), editorHost, createDivider(), actions);
    container.replaceChildren(card);
    container.hidden = false;

    createCodeEditorView({
        parent: editorHost,
        document: sourceCode,
        language: 'python',
        onChange: (value) => {
            sourceCode = value;
        },
    });
};
