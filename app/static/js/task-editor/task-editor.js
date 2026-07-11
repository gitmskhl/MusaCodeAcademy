import { createCodeEditorView } from '../step-renderer/codemirror/code-editor-view.js';

const TOKEN_KEY = 'musa_code_academy_token';

const getToken = () => localStorage.getItem(TOKEN_KEY);

const clearToken = () => localStorage.removeItem(TOKEN_KEY);

const redirectDashboard = () => {
    window.location.replace('/dashboard');
};

const elements = {
    root: document.querySelector('[data-task-editor]'),
    form: document.querySelector('[data-task-form]'),
    backButton: document.querySelector('[data-back-button]'),
    saveButton: document.querySelector('[data-save-button]'),
    saveStatus: document.querySelector('[data-save-status]'),
    starterCodeEditor: document.querySelector('[data-starter-code-editor]'),
    timeLimit: document.querySelector('[data-time-limit]'),
    memoryLimit: document.querySelector('[data-memory-limit]'),
    testZip: document.querySelector('[data-test-zip]'),
    uploadTestsButton: document.querySelector('[data-upload-tests]'),
    testUploadStatus: document.querySelector('[data-test-upload-status]'),
    testCasesTableWrap: document.querySelector('[data-test-cases-table-wrap]'),
    testCasesBody: document.querySelector('[data-test-cases-body]'),
    testCasesEmpty: document.querySelector('[data-test-cases-empty]'),
};

const state = {
    task: null,
    starterCode: '',
    codeEditor: null,
    saveStatusTimer: null,
    testCases: [],
};

const getStepId = () => {
    const stepId = Number(elements.root?.dataset.stepId);
    return Number.isInteger(stepId) && stepId > 0 ? stepId : null;
};

const setSaveStatus = (message, { error = false } = {}) => {
    window.clearTimeout(state.saveStatusTimer);
    elements.saveStatus.classList.toggle('is-error', error);
    elements.saveStatus.textContent = message;
};

const getResponseErrorMessage = async (response, fallback) => {
    try {
        const data = await response.json();
        if (Array.isArray(data.detail)) {
            return data.detail
                .map((item) => {
                    const field = item.loc?.at(-1);
                    return field ? `${field}: ${item.msg}` : item.msg;
                })
                .join(' ');
        }
        if (typeof data.detail === 'string') {
            return data.detail;
        }
    } catch {
        // The response has no JSON error body.
    }
    return `${fallback} (${response.status}).`;
};

const authFetch = async (input, init = {}) => {
    const token = getToken();
    if (!token) {
        redirectDashboard();
        throw new Error('authentication-required');
    }

    const headers = new Headers(init.headers || {});
    headers.set('Authorization', `Bearer ${token}`);

    const response = await fetch(input, { ...init, headers });
    if (response.status === 401) {
        clearToken();
        redirectDashboard();
        throw new Error('authentication-required');
    }
    return response;
};

const checkAdminAccess = async () => {
    const response = await authFetch('/api/users/me');
    if (!response.ok) {
        redirectDashboard();
        return false;
    }

    const user = await response.json();
    if (user.role !== 'admin') {
        redirectDashboard();
        return false;
    }

    return true;
};

const setEditorLoading = (loading) => {
    elements.saveButton.disabled = loading;
    elements.timeLimit.disabled = loading;
    elements.memoryLimit.disabled = loading;
    elements.testZip.disabled = loading || !state.task?.id;
    elements.uploadTestsButton.disabled = loading || !state.task?.id;
    state.codeEditor?.setEditable(!loading);
};

const setTaskValues = (task) => {
    state.task = task;
    state.starterCode = task?.starter_code ?? '';
    elements.timeLimit.value = String(task?.time_limit_ms ?? 1000);
    elements.memoryLimit.value = String(task?.memory_limit_mb ?? 128);
};

const mountCodeEditor = () => {
    state.codeEditor = createCodeEditorView({
        parent: elements.starterCodeEditor,
        document: state.starterCode,
        language: 'python',
        onChange: (value) => {
            state.starterCode = value;
        },
    });
};

const loadTask = async () => {
    const stepId = getStepId();
    if (!stepId) {
        throw new Error('Invalid step ID.');
    }

    let response = await authFetch(`/api/steps/${encodeURIComponent(stepId)}/task`);
    if (response.status >= 500) {
        response = await authFetch(
            `/api/tasks/admin/by-step/${encodeURIComponent(stepId)}`
        );
    }
    if (response.status === 404) {
        setTaskValues(null);
        return;
    }
    if (!response.ok) {
        throw new Error(
            await getResponseErrorMessage(response, 'Failed to load task')
        );
    }

    setTaskValues(await response.json());
};

const setTestUploadStatus = (message, { error = false } = {}) => {
    elements.testUploadStatus.classList.toggle('is-error', error);
    elements.testUploadStatus.textContent = message;
};

const truncateTestValue = (value) => {
    const compactValue = String(value ?? '').replace(/[\r\n]+/g, ' ');
    return compactValue.length > 100
        ? `${compactValue.slice(0, 100)}...`
        : compactValue;
};

const createActionButton = ({ label, path }) => {
    const button = document.createElement('button');
    button.className = 'test-case-action';
    button.type = 'button';
    button.setAttribute('aria-label', label);
    button.title = `${label} (coming soon)`;
    button.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"/></svg>`;
    return button;
};

const renderTestCases = () => {
    elements.testCasesBody.replaceChildren();
    const hasTestCases = state.testCases.length > 0;
    elements.testCasesTableWrap.hidden = !hasTestCases;
    elements.testCasesEmpty.hidden = hasTestCases;

    state.testCases.forEach((testCase, index) => {
        const row = document.createElement('tr');
        const numberCell = document.createElement('td');
        numberCell.textContent = String(testCase.order ?? index + 1);

        const inputCell = document.createElement('td');
        const inputValue = document.createElement('span');
        inputValue.className = 'test-cases-table__value';
        inputValue.textContent = truncateTestValue(testCase.input);
        inputValue.title = String(testCase.input ?? '');
        inputCell.append(inputValue);

        const outputCell = document.createElement('td');
        const outputValue = document.createElement('span');
        outputValue.className = 'test-cases-table__value';
        outputValue.textContent = truncateTestValue(testCase.expected_output);
        outputValue.title = String(testCase.expected_output ?? '');
        outputCell.append(outputValue);

        const actionsCell = document.createElement('td');
        actionsCell.className = 'test-cases-table__actions';
        actionsCell.append(
            createActionButton({
                label: 'Edit test case',
                path: 'M12 20h9 M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z',
            }),
            createActionButton({
                label: 'Delete test case',
                path: 'M3 6h18 M8 6V4h8v2 M19 6l-1 14H6L5 6 M10 11v5 M14 11v5',
            })
        );

        row.append(numberCell, inputCell, outputCell, actionsCell);
        elements.testCasesBody.append(row);
    });
};

const loadTestCases = async () => {
    if (!state.task?.id) {
        state.testCases = [];
        renderTestCases();
        return;
    }

    const response = await authFetch(
        `/api/test-cases/admin/by-task/${encodeURIComponent(state.task.id)}`
    );
    if (!response.ok) {
        throw new Error(
            await getResponseErrorMessage(response, 'Failed to load test cases')
        );
    }

    state.testCases = await response.json();
    renderTestCases();
};

const uploadTests = async () => {
    const file = elements.testZip.files?.[0];
    if (!state.task?.id) {
        setTestUploadStatus('Save the task before uploading tests.', { error: true });
        return;
    }
    if (!file) {
        setTestUploadStatus('Select a ZIP archive to upload.', { error: true });
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    elements.testZip.disabled = true;
    elements.uploadTestsButton.disabled = true;
    setTestUploadStatus('Uploading test cases...');

    try {
        const response = await authFetch(
            `/api/tasks/${encodeURIComponent(state.task.id)}/tests/upload`,
            { method: 'POST', body: formData }
        );
        if (!response.ok) {
            throw new Error(
                await getResponseErrorMessage(response, 'Failed to upload tests')
            );
        }

        await loadTestCases();
        elements.testZip.value = '';
        setTestUploadStatus('Test cases uploaded successfully.');
    } catch (error) {
        setTestUploadStatus(
            error instanceof Error && error.message
                ? error.message
                : 'Failed to upload tests.',
            { error: true }
        );
    } finally {
        elements.testZip.disabled = false;
        elements.uploadTestsButton.disabled = false;
    }
};

const getNumberFieldValue = (input, fallback) => {
    const value = Number(input.value);
    return Number.isFinite(value) ? value : fallback;
};

const buildPayload = () => ({
    starter_code: state.starterCode || null,
    time_limit_ms: getNumberFieldValue(elements.timeLimit, 1000),
    memory_limit_mb: getNumberFieldValue(elements.memoryLimit, 128),
});

const saveTask = async () => {
    const stepId = getStepId();
    if (!stepId) {
        setSaveStatus('Invalid step ID.', { error: true });
        return;
    }

    const payload = buildPayload();
    const isExistingTask = Boolean(state.task?.id);
    const url = isExistingTask
        ? `/api/tasks/admin/${encodeURIComponent(state.task.id)}`
        : '/api/tasks/admin';
    const method = isExistingTask ? 'PATCH' : 'POST';
    const body = JSON.stringify(
        isExistingTask ? payload : { step_id: stepId, ...payload }
    );

    elements.saveButton.disabled = true;
    elements.saveButton.textContent = 'Сохранение...';
    setSaveStatus('');

    try {
        const response = await authFetch(url, {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
            body,
        });

        if (!response.ok) {
            throw new Error(
                await getResponseErrorMessage(response, 'Failed to save task')
            );
        }

        state.task = await response.json();
        elements.testZip.disabled = false;
        elements.uploadTestsButton.disabled = false;
        elements.saveButton.textContent = 'Сохранено';
        setSaveStatus('Изменения сохранены.');
        state.saveStatusTimer = window.setTimeout(() => {
            elements.saveButton.textContent = 'Сохранить';
            elements.saveStatus.textContent = '';
        }, 1800);
    } catch (error) {
        elements.saveButton.textContent = 'Сохранить';
        setSaveStatus(
            error instanceof Error && error.message
                ? error.message
                : 'Failed to save task.',
            { error: true }
        );
    } finally {
        elements.saveButton.disabled = false;
    }
};

const bindEvents = () => {
    elements.saveButton.addEventListener('click', saveTask);
    elements.form.addEventListener('submit', (event) => {
        event.preventDefault();
        saveTask();
    });
    elements.uploadTestsButton.addEventListener('click', uploadTests);
    elements.testZip.addEventListener('change', () => setTestUploadStatus(''));

    elements.backButton.addEventListener('click', (event) => {
        if (window.history.length > 1) {
            event.preventDefault();
            window.history.back();
        }
    });
};

const init = async () => {
    if (!elements.root) {
        return;
    }

    setEditorLoading(true);
    setSaveStatus('Загрузка...');

    try {
        const hasAccess = await checkAdminAccess();
        if (!hasAccess) {
            return;
        }

        await loadTask();
        await loadTestCases();
        mountCodeEditor();
        bindEvents();
        setSaveStatus('');
        setEditorLoading(false);
    } catch (error) {
        if (error instanceof Error && error.message === 'authentication-required') {
            return;
        }
        setSaveStatus(
            error instanceof Error && error.message
                ? error.message
                : 'Failed to load task.',
            { error: true }
        );
    }
};

init();
