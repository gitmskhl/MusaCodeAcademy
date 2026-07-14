const STATUS_CONFIG = {
    PENDING: {
        tone: 'pending', icon: '⏳', title: 'Waiting in queue...', progress: 25,
        message: 'Your solution has been added to the queue and is waiting for a free worker.',
    },
    RUNNING: {
        tone: 'running', icon: '', title: 'Running tests...', progress: 70,
        message: 'Your solution is currently being checked.', spinner: true,
    },
    ACCEPTED: {
        tone: 'accepted', icon: '✓', title: 'Accepted', progress: 100,
        message: 'All tests passed.',
    },
    WRONG_ANSWER: {
        tone: 'error', icon: '✕', title: 'Wrong Answer', progress: 100, failed: true,
    },
    RUNTIME_ERROR: {
        tone: 'error', icon: '✕', title: 'Runtime Error', progress: 100, failed: true,
    },
    TIME_LIMIT_EXCEEDED: {
        tone: 'error', icon: '✕', title: 'Time Limit Exceeded', progress: 100, failed: true,
    },
    SYSTEM_ERROR: {
        tone: 'warning', icon: '!', title: 'System Error', progress: 100,
        message: 'An internal error occurred while checking your solution. Please try again.',
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

export const createSubmissionStatusPanel = ({ fetcher }) => {
    let renderVersion = 0;
    let currentRenderKey = null;
    const card = createElement('article', 'submission-status');
    const heading = createElement('h3', 'submission-status__heading', 'Last submission');
    const body = createElement('div', 'submission-status__body');
    card.append(heading, body);

    const renderEmpty = () => {
        if (currentRenderKey === 'empty') return;
        currentRenderKey = 'empty';
        renderVersion += 1;
        card.dataset.tone = 'empty';
        body.replaceChildren(createElement('p', 'submission-status__empty', 'No submissions yet.'));
    };

    const renderTestDetails = async (testCaseId, detailsHost, button, version) => {
        button.disabled = true;
        button.textContent = 'Loading test...';
        try {
            const response = await fetcher(`/api/test-cases/${encodeURIComponent(testCaseId)}`);
            if (version !== renderVersion) return;

            if (response.status === 403 || response.status === 404) {
                detailsHost.replaceChildren(createElement(
                    'p', 'submission-status__hidden-message',
                    'This test is hidden and cannot be viewed.'
                ));
                button.remove();
                return;
            }
            if (!response.ok) throw new Error('failed-test-request-failed');

            const testCase = await response.json();
            if (version !== renderVersion) return;

            const details = createElement('details', 'submission-status__test-details');
            details.open = true;
            details.append(createElement('summary', 'submission-status__test-summary', 'Failed test details'));
            const content = createElement('div', 'submission-status__test-content');
            const input = testCase.input ?? '';
            const copyButton = createElement('button', 'submission-status__copy', 'Copy input');
            copyButton.type = 'button';
            copyButton.addEventListener('click', async () => {
                try {
                    await copyText(input);
                    copyButton.textContent = 'Copied';
                    window.setTimeout(() => {
                        if (copyButton.isConnected) copyButton.textContent = 'Copy input';
                    }, 1500);
                } catch {
                    copyButton.textContent = 'Could not copy';
                }
            });
            content.append(
                createTestValue('Test input', input),
                copyButton,
                createTestValue('Expected output', testCase.expected_output ?? '')
            );
            details.append(content);
            detailsHost.replaceChildren(details);
            button.remove();
        } catch (error) {
            if (version !== renderVersion || error.message === 'authentication-required') return;
            button.disabled = false;
            button.textContent = 'Show failed test';
            detailsHost.replaceChildren(createElement(
                'p', 'submission-status__load-error',
                'Could not load this test. Please try again.'
            ));
        }
    };

    const render = (submission) => {
        if (!submission) {
            renderEmpty();
            return;
        }

        const status = normalizeStatus(submission.status);
        const renderKey = JSON.stringify([
            status,
            submission.passed_tests,
            submission.total_tests,
            submission.test_case_id ?? submission.failed_test_id,
        ]);
        if (renderKey === currentRenderKey) return;
        currentRenderKey = renderKey;
        const version = ++renderVersion;
        const config = STATUS_CONFIG[status] || {
            tone: 'warning', icon: '!', title: String(submission.status || 'Unknown status'),
            progress: 100, message: 'The submission finished with an unknown status.',
        };
        card.dataset.tone = config.tone;

        const statusRow = createElement('div', 'submission-status__status-row');
        const icon = createElement('span', 'submission-status__icon', config.icon);
        icon.setAttribute('aria-hidden', 'true');
        if (config.spinner) icon.classList.add('submission-status__icon--spinner');
        statusRow.append(icon, createElement('h4', 'submission-status__title', config.title));

        const progress = createElement('div', 'submission-status__progress');
        progress.setAttribute('role', 'progressbar');
        progress.setAttribute('aria-label', 'Submission progress');
        progress.setAttribute('aria-valuemin', '0');
        progress.setAttribute('aria-valuemax', '100');
        progress.setAttribute('aria-valuenow', String(config.progress));
        const progressValue = createElement('span', 'submission-status__progress-value');
        progressValue.style.width = `${config.progress}%`;
        progress.append(progressValue);

        const content = createElement('div', 'submission-status__content');
        if (config.failed) {
            const hasPassedTests = Number.isFinite(submission.passed_tests);
            content.append(createElement(
                'p', 'submission-status__message',
                `Passed tests: ${hasPassedTests ? submission.passed_tests : 0}`
            ));
            if (hasPassedTests) {
                content.append(createElement(
                    'p', 'submission-status__failed-on',
                    `Failed on test #${submission.passed_tests + 1}`
                ));
            }
        } else {
            content.append(createElement('p', 'submission-status__message', config.message));
        }

        const testCaseId = submission.test_case_id ?? submission.failed_test_id;
        if (config.failed && testCaseId != null) {
            const button = createElement('button', 'submission-status__show-test', 'Show failed test');
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
