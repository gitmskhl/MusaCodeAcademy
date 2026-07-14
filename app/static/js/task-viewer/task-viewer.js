import { createCodeEditorView } from '../step-renderer/codemirror/code-editor-view.js';
import { authFetch } from '../course-auth.js';
import { createSubmissionStatusPanel } from './submission-status-panel.js';

const SUBMIT_LABEL = 'Отправить решение';
const SUBMITTING_LABEL = 'Отправляем решение...';
const POLLING_INTERVAL_MS = 1000;
const ACTIVE_SUBMISSION_STATUSES = new Set(['PENDING', 'RUNNING']);

let cleanupActiveTaskViewer = () => {};

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
    cleanupActiveTaskViewer();
    container.replaceChildren();
    container.hidden = true;
};

export const renderTaskError = (container, message) => {
    cleanupActiveTaskViewer();
    const card = document.createElement('article');
    card.className = 'task-viewer__card task-viewer__card--error';
    card.setAttribute('role', 'alert');
    card.textContent = message;

    container.replaceChildren(card);
    container.hidden = false;
};

export const renderTaskViewer = (container, task) => {
    cleanupActiveTaskViewer();

    let sourceCode = task.starter_code || '';
    let latestSubmissionStatus = null;
    let pollingTimer = null;
    let isPollingRequest = false;
    let isSubmitting = false;
    let isDestroyed = false;

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
    actions.append(submitStatus, submitButton);
    card.append(header, createDivider(), editorHost, createDivider(), actions);

    const statusPanel = createSubmissionStatusPanel({ fetcher: authFetch });
    container.replaceChildren(card, statusPanel.element);
    container.hidden = false;

    const editor = createCodeEditorView({
        parent: editorHost,
        document: sourceCode,
        language: 'python',
        onChange: (value) => {
            sourceCode = value;
        },
    });

    const stopPolling = () => {
        if (pollingTimer !== null) {
            window.clearTimeout(pollingTimer);
            pollingTimer = null;
        }
    };

    const displaySubmission = (submission, { loadSource = false } = {}) => {
        if (!submission) {
            latestSubmissionStatus = null;
            stopPolling();
            submitButton.disabled = false;
            submitButton.textContent = SUBMIT_LABEL;
            statusPanel.render(null);
            return false;
        }

        if (loadSource) {
            sourceCode = submission.source_code;
            editor.setDocument(sourceCode);
        }

        latestSubmissionStatus = submission.status;
        statusPanel.render(submission);
        submitStatus.textContent = '';
        submitStatus.classList.remove('is-error');

        const isActive = ACTIVE_SUBMISSION_STATUSES.has(submission.status);
        submitButton.disabled = isActive;
        submitButton.textContent = SUBMIT_LABEL;
        if (!isActive) {
            stopPolling();
        }
        return isActive;
    };

    const getLastSubmission = async () => {
        const response = await authFetch(
            `/api/tasks/${encodeURIComponent(task.id)}/submissions/last`
        );
        if (!response.ok) {
            throw new Error('last-submission-request-failed');
        }
        return response.json();
    };

    const startPolling = () => {
        if (isDestroyed || pollingTimer !== null || isPollingRequest) {
            return;
        }

        pollingTimer = window.setTimeout(async () => {
            pollingTimer = null;
            isPollingRequest = true;
            let shouldContinue = true;
            try {
                const submission = await getLastSubmission();
                if (isDestroyed) {
                    return;
                }
                shouldContinue = displaySubmission(submission);
            } catch {
                // Retry transient failures while the submission is active.
            } finally {
                isPollingRequest = false;
                if (shouldContinue && !isDestroyed) {
                    startPolling();
                }
            }
        }, POLLING_INTERVAL_MS);
    };

    const loadLastSubmission = async () => {
        try {
            const submission = await getLastSubmission();
            if (!isDestroyed && displaySubmission(submission, { loadSource: true })) {
                startPolling();
            }
        } catch {
            // The editor stays usable if submission history is unavailable.
        }
    };

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

            const submission = await response.json();
            if (displaySubmission(submission)) {
                startPolling();
            }
        } catch (error) {
            latestSubmissionStatus = null;
            if (error.message !== 'authentication-required') {
                submitStatus.textContent = error.message || 'Не удалось отправить решение.';
                submitStatus.classList.add('is-error');
            }
        } finally {
            isSubmitting = false;
            if (!ACTIVE_SUBMISSION_STATUSES.has(latestSubmissionStatus)) {
                submitButton.disabled = false;
            }
            submitButton.textContent = SUBMIT_LABEL;
        }
    });

    const cleanup = () => {
        if (isDestroyed) {
            return;
        }
        isDestroyed = true;
        stopPolling();
        editor.destroy();
        window.removeEventListener('pagehide', cleanup);
        if (cleanupActiveTaskViewer === cleanup) {
            cleanupActiveTaskViewer = () => {};
        }
    };

    cleanupActiveTaskViewer = cleanup;
    window.addEventListener('pagehide', cleanup, { once: true });
    loadLastSubmission();
};
