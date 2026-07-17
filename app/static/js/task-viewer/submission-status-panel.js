const STATUS_CONFIG = {
    PENDING: {
        tone: 'pending', icon: '\u23f3', title: 'Ожидание в очереди…', progress: 25,
        message: 'Ваше решение добавлено в очередь и ожидает свободного обработчика.',
    },
    RUNNING: {
        tone: 'running', icon: '', title: 'Проверка решения…', progress: 70,
        message: 'Ваше решение сейчас проходит проверку.', spinner: true,
    },
    ACCEPTED: {
        tone: 'accepted', icon: '\u2713', title: 'Принято', progress: 100,
        message: 'Все тесты пройдены.',
    },
    WRONG_ANSWER: {
        tone: 'error', icon: '\u2715', title: 'Неверный ответ', progress: 100, failed: true,
    },
    RUNTIME_ERROR: {
        tone: 'error', icon: '\u2715', title: 'Ошибка выполнения', progress: 100, failed: true,
    },
    TIME_LIMIT_EXCEEDED: {
        tone: 'error', icon: '\u2715', title: 'Превышено ограничение времени', progress: 100, failed: true,
    },
    MEMORY_LIMIT_EXCEEDED: {
        tone: 'error', icon: '\u2715', title: 'Превышено ограничение памяти', progress: 100,
        message: 'Превышено ограничение по памяти.',
    },
    SYSTEM_ERROR: {
        tone: 'warning', icon: '!', title: 'Системная ошибка', progress: 100,
        message: 'Во время проверки произошла внутренняя ошибка. Пожалуйста, попробуйте ещё раз.',
    },
};

const normalizeStatus = (status) =>
    String(status || '').trim().toUpperCase().replace(/[\s-]+/g, '_');

const createElement = (tag, className, text) => {
    const element = document.createElement(tag);
    element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
};

const copyText = async (text) => {
    if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        return;
    }
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.append(textarea);
    textarea.select();
    document.execCommand('copy');
    textarea.remove();
};

const createTestValue = (label, value) => {
    const group = createElement('div', 'submission-status__test-group');
    group.append(
        createElement('h5', 'submission-status__test-label', label),
        createElement('pre', 'submission-status__test-value', value || '')
    );
    return group;
};

const getRunResult = (submission) => submission.run_result ?? submission.result ?? submission;

const hasValue = (value) => value !== null && value !== undefined;

const hasOutput = (value) => typeof value === 'string' && value.trim() !== '';

const getRuntimeErrorMessage = (runResult) => {
    if (runResult.timed_out === true) {
        return 'Превышено ограничение по времени выполнения.';
    }
    if (runResult.oom_killed === true) {
        return 'Превышено ограничение по памяти.';
    }
    if (
        runResult.timed_out === false &&
        runResult.oom_killed === false &&
        hasValue(runResult.exit_code) &&
        runResult.exit_code !== 0
    ) {
        return 'Ошибка выполнения программы.';
    }
    return null;
};

const createResultSection = (label, content, { code = false, strong = false } = {}) => {
    const section = createElement('section', 'submission-status__result-section');
    section.append(createElement('h5', 'submission-status__result-label', label));

    if (code) {
        section.append(createElement('pre', 'submission-status__result-code', content));
        return section;
    }

    const value = createElement('p', 'submission-status__result-value', content);
    if (strong) value.classList.add('submission-status__result-value--strong');
    section.append(value);
    return section;
};

const appendExecutionTime = (content, runResult) => {
    if (!hasValue(runResult.execution_time_ms)) return;
    content.append(createResultSection(
        'Время выполнения',
        `${runResult.execution_time_ms} мс`
    ));
};

const appendRuntimeResultDetails = (content, runResult) => {
    const errorMessage = getRuntimeErrorMessage(runResult);
    if (!errorMessage) return false;
    const isRuntimeError = runResult.timed_out === false && runResult.oom_killed === false;

    content.append(createResultSection('Ошибка', errorMessage, { strong: true }));
    appendExecutionTime(content, runResult);

    if (
        isRuntimeError &&
        hasValue(runResult.exit_code)
    ) {
        content.append(createResultSection('Код завершения', String(runResult.exit_code)));
    }

    if (isRuntimeError && hasOutput(runResult.stderr)) {
        content.append(createResultSection('Standard Error (stderr)', runResult.stderr, { code: true }));
    }
    if (hasOutput(runResult.stdout)) {
        content.append(createResultSection('Standard Output (stdout)', runResult.stdout, { code: true }));
    }
    if (!isRuntimeError && hasOutput(runResult.stderr)) {
        content.append(createResultSection('Standard Error (stderr)', runResult.stderr, { code: true }));
    }

    return true;
};

export const createSubmissionStatusPanel = ({ fetcher }) => {
    let renderVersion = 0;
    let currentRenderKey = null;
    const card = createElement('article', 'submission-status');
    const heading = createElement('h3', 'submission-status__heading', 'Последняя отправка');
    const body = createElement('div', 'submission-status__body');
    card.append(heading, body);

    const renderEmpty = () => {
        if (currentRenderKey === 'empty') return;
        currentRenderKey = 'empty';
        renderVersion += 1;
        card.dataset.tone = 'empty';
        card.hidden = true;
        body.replaceChildren(createElement('p', 'submission-status__empty', 'Отправок пока нет.'));
    };

    const renderTestDetails = async (testCaseId, detailsHost, button, version) => {
        button.disabled = true;
        button.textContent = 'Загрузка теста…';
        try {
            const response = await fetcher(`/api/test-cases/${encodeURIComponent(testCaseId)}`);
            if (version !== renderVersion) return;

            if (response.status === 403 || response.status === 404) {
                detailsHost.replaceChildren(createElement(
                    'p', 'submission-status__hidden-message',
                    'Этот тест скрыт и недоступен для просмотра.'
                ));
                button.remove();
                return;
            }
            if (!response.ok) throw new Error('failed-test-request-failed');

            const testCase = await response.json();
            if (version !== renderVersion) return;

            const details = createElement('details', 'submission-status__test-details');
            details.open = true;
            details.append(createElement('summary', 'submission-status__test-summary', 'Детали непройденного теста'));
            const content = createElement('div', 'submission-status__test-content');
            const input = testCase.input ?? '';
            const copyButton = createElement('button', 'submission-status__copy', 'Копировать входные данные');
            copyButton.type = 'button';
            copyButton.addEventListener('click', async () => {
                try {
                    await copyText(input);
                    copyButton.textContent = 'Скопировано';
                    window.setTimeout(() => {
                        if (copyButton.isConnected) copyButton.textContent = 'Копировать входные данные';
                    }, 1500);
                } catch {
                    copyButton.textContent = 'Не удалось скопировать';
                }
            });
            content.append(
                createTestValue('Входные данные', input),
                copyButton,
                createTestValue('Ожидаемый результат', testCase.expected_output ?? '')
            );
            details.append(content);
            detailsHost.replaceChildren(details);
            button.remove();
        } catch (error) {
            if (version !== renderVersion || error.message === 'authentication-required') return;
            button.disabled = false;
            button.textContent = 'Показать непройденный тест';
            detailsHost.replaceChildren(createElement(
                'p', 'submission-status__load-error',
                'Не удалось загрузить тест. Попробуйте ещё раз.'
            ));
        }
    };

    const render = (submission) => {
        if (!submission) {
            renderEmpty();
            return;
        }

        const status = normalizeStatus(submission.status);
        const runResult = getRunResult(submission);
        const renderKey = JSON.stringify([
            status,
            submission.passed_tests,
            submission.total_tests,
            submission.test_case_id ?? submission.failed_test_id,
            runResult.stdout,
            runResult.stderr,
            runResult.exit_code,
            runResult.execution_time_ms,
            runResult.timed_out,
            runResult.oom_killed,
        ]);
        if (renderKey === currentRenderKey) return;
        currentRenderKey = renderKey;
        const version = ++renderVersion;
        const config = STATUS_CONFIG[status] || {
            tone: 'warning', icon: '!', title: 'Неизвестный статус',
            progress: 100, message: 'Проверка завершилась с неизвестным статусом.',
        };
        card.hidden = false;
        card.dataset.tone = config.tone;

        const statusRow = createElement('div', 'submission-status__status-row');
        const icon = createElement('span', 'submission-status__icon', config.icon);
        icon.setAttribute('aria-hidden', 'true');
        if (config.spinner) icon.classList.add('submission-status__icon--spinner');
        statusRow.append(icon, createElement('h4', 'submission-status__title', config.title));

        const progress = createElement('div', 'submission-status__progress');
        progress.setAttribute('role', 'progressbar');
        progress.setAttribute('aria-label', 'Ход проверки решения');
        progress.setAttribute('aria-valuemin', '0');
        progress.setAttribute('aria-valuemax', '100');
        progress.setAttribute('aria-valuenow', String(config.progress));
        const progressValue = createElement('span', 'submission-status__progress-value');
        progressValue.style.width = `${config.progress}%`;
        progress.append(progressValue);

        const content = createElement('div', 'submission-status__content');
        const hasRuntimeResultDetails = appendRuntimeResultDetails(content, runResult);
        if (!hasRuntimeResultDetails && config.failed) {
            const hasPassedTests = Number.isFinite(submission.passed_tests);
            content.append(createElement(
                'p', 'submission-status__message',
                `Пройдено тестов: ${hasPassedTests ? submission.passed_tests : 0}`
            ));
            if (hasPassedTests) {
                content.append(createElement(
                    'p', 'submission-status__failed-on',
                    `Не пройден тест №${submission.passed_tests + 1}`
                ));
            }
        } else if (!hasRuntimeResultDetails) {
            content.append(createElement('p', 'submission-status__message', config.message));
        }
        if (!hasRuntimeResultDetails) {
            appendExecutionTime(content, runResult);
        }

        const testCaseId = submission.test_case_id ?? submission.failed_test_id;
        if (config.failed && !hasRuntimeResultDetails && testCaseId != null) {
            const button = createElement('button', 'submission-status__show-test', 'Показать непройденный тест');
            button.type = 'button';
            const detailsHost = createElement('div', 'submission-status__details-host');
            button.addEventListener('click', () => {
                renderTestDetails(testCaseId, detailsHost, button, version);
            });
            content.append(button, detailsHost);
        }

        body.replaceChildren(statusRow, progress, content);
        body.classList.remove('is-transitioning');
        void body.offsetWidth;
        body.classList.add('is-transitioning');
    };

    renderEmpty();
    return { element: card, render };
};
