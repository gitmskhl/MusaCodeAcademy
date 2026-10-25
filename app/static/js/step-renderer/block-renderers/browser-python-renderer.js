import { mountCodeEditor } from '../codemirror/code-editor-instance.js';

const PYODIDE_INDEX_URL = 'https://cdn.jsdelivr.net/pyodide/v0.29.4/full/';

const escapeScriptContent = (value) =>
    String(value).replaceAll('</script', '<\\/script');

const createScriptStringLiteral = (value) =>
    escapeScriptContent(JSON.stringify(value));

const createRunnerId = () => {
    if (globalThis.crypto?.randomUUID) {
        return globalThis.crypto.randomUUID();
    }
    const randomPart = Math.random().toString(36).slice(2);
    return `browser-python-${Date.now()}-${randomPart}`;
};

const createRunnerDocument = (code, stdin, runnerId) => `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<script src="${PYODIDE_INDEX_URL}pyodide.js"><\/script>
</head>
<body>
<script>
(async () => {
    const runnerId = ${JSON.stringify(runnerId)};
    const code = ${createScriptStringLiteral(code)};
    const stdin = ${createScriptStringLiteral(stdin)};
    const post = (type, payload = {}) => {
        parent.postMessage({
            source: 'browser-python-runner',
            runnerId,
            type,
            ...payload
        }, '*');
    };

    try {
        post('status', {
            state: 'loading_runtime',
            message: 'Загружается Python'
        });
        const pyodide = await loadPyodide({
            indexURL: ${JSON.stringify(PYODIDE_INDEX_URL)}
        });

        post('status', {
            state: 'loading_packages',
            message: 'Загружаются пакеты'
        });
        await pyodide.loadPackagesFromImports(code);

        pyodide.globals.set('__runner_code', code);
        pyodide.globals.set('__runner_stdin_text', stdin);
        post('status', { state: 'running', message: 'Выполняется' });
        await pyodide.runPythonAsync(\`
import contextlib
import io
import sys
import traceback

__runner_stdout = io.StringIO()
__runner_stderr = io.StringIO()
__runner_stdin = io.StringIO(__runner_stdin_text)
__runner_original_stdin = sys.stdin

sys.stdin = __runner_stdin
with contextlib.redirect_stdout(__runner_stdout), contextlib.redirect_stderr(__runner_stderr):
    try:
        exec(__runner_code, globals())
    except Exception:
        traceback.print_exc(file=__runner_stderr)
    finally:
        sys.stdin = __runner_original_stdin
\`);

        post('result', {
            stdout: pyodide.globals.get('__runner_stdout').getvalue(),
            stderr: pyodide.globals.get('__runner_stderr').getvalue()
        });
        post('status', { state: 'done', message: 'Готово' });
    } catch (error) {
        post('error', {
            message: error instanceof Error ? error.message : String(error)
        });
        post('status', { state: 'failed', message: 'Ошибка' });
    }
})();
<\/script>
</body>
</html>`;

const createOutputLine = ({ level, message }) => {
    const line = document.createElement('div');
    line.className = `browser-code__output-line browser-code__output-line--${level}`;
    line.textContent = message;
    return line;
};

export const renderBrowserPythonBlock = (
    block,
    { index, onChange = () => {} } = {}
) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'browser-code';
    let runnerId = null;
    let running = false;
    let hasResult = false;
    let currentCode = block.data?.code ?? '';
    let currentStdin = block.data?.stdin ?? '';

    const toolbar = document.createElement('div');
    toolbar.className = 'browser-code__toolbar';

    const runButton = document.createElement('button');
    runButton.className = 'browser-code__run';
    runButton.type = 'button';
    runButton.textContent = 'Запустить';

    const stopButton = document.createElement('button');
    stopButton.className = 'browser-code__stop';
    stopButton.type = 'button';
    stopButton.textContent = 'Остановить';
    stopButton.disabled = true;

    const status = document.createElement('span');
    status.className = 'browser-code__status';
    status.textContent = 'Python выполняется в вашем браузере';

    toolbar.append(runButton, stopButton, status);

    const sources = document.createElement('div');
    sources.className = 'browser-code__sources browser-code__sources--python';

    mountCodeEditor({
        block,
        index,
        language: 'python',
        parent: sources,
        editable: true,
        onChange: (value) => {
            currentCode = value;
            onChange({ code: value });
        },
    });

    const inputPanel = document.createElement('label');
    inputPanel.className = 'browser-code__stdin-field';

    const inputLabel = document.createElement('span');
    inputLabel.className = 'browser-code__stdin-label';
    inputLabel.textContent = 'Входные данные';

    const inputHelp = document.createElement('span');
    inputHelp.className = 'browser-code__stdin-help';
    inputHelp.textContent = 'Каждая строка используется для очередного input().';

    const stdinInput = document.createElement('textarea');
    stdinInput.className = 'browser-code__stdin';
    stdinInput.spellcheck = false;
    stdinInput.rows = 4;
    stdinInput.placeholder = 'Например:\nпример\n18';
    stdinInput.value = currentStdin;
    stdinInput.addEventListener('input', () => {
        currentStdin = stdinInput.value;
        onChange({ stdin: stdinInput.value });
    });

    inputPanel.append(inputLabel, inputHelp, stdinInput);

    const frame = document.createElement('iframe');
    frame.className = 'browser-code__frame';
    frame.title = 'Browser Python runtime';
    frame.sandbox = 'allow-scripts';

    const output = document.createElement('div');
    output.className = 'browser-code__output';
    output.setAttribute('aria-live', 'polite');

    const setInitialOutput = () => {
        output.replaceChildren(
            createOutputLine({
                level: 'info',
                message: 'Здесь появится вывод Python.',
            })
        );
    };

    const appendOutput = ({ level, message }) => {
        if (!message.trim()) {
            return;
        }
        if (!hasResult) {
            output.replaceChildren();
            hasResult = true;
        }
        output.appendChild(createOutputLine({ level, message }));
    };

    const setRunning = (nextRunning) => {
        running = nextRunning;
        runButton.disabled = nextRunning;
        stopButton.disabled = !nextRunning;
    };

    const stop = ({ message = 'Остановлено' } = {}) => {
        if (!running) {
            return;
        }
        runnerId = null;
        frame.removeAttribute('srcdoc');
        setRunning(false);
        status.textContent = message;
    };

    const run = () => {
        runnerId = createRunnerId();
        hasResult = false;
        setRunning(true);
        setInitialOutput();
        frame.srcdoc = createRunnerDocument(
            currentCode,
            currentStdin,
            runnerId
        );
        status.textContent = 'Запуск';
    };

    const messageHandler = (event) => {
        if (!wrapper.isConnected) {
            stop({ message: '' });
            window.removeEventListener('message', messageHandler);
            return;
        }

        const data = event.data;
        if (
            data?.source !== 'browser-python-runner' ||
            data.runnerId !== runnerId
        ) {
            return;
        }

        if (data.type === 'status') {
            status.textContent = data.message ?? '';
            if (data.state === 'done' || data.state === 'failed') {
                setRunning(false);
            }
            return;
        }

        if (data.type === 'result') {
            appendOutput({ level: 'info', message: data.stdout ?? '' });
            appendOutput({ level: 'error', message: data.stderr ?? '' });
            if (!hasResult) {
                output.replaceChildren(
                    createOutputLine({
                        level: 'info',
                        message: 'Нет вывода.',
                    })
                );
                hasResult = true;
            }
            return;
        }

        if (data.type === 'error') {
            appendOutput({ level: 'error', message: data.message ?? '' });
        }
    };

    runButton.addEventListener('click', run);
    stopButton.addEventListener('click', () => stop());
    window.addEventListener('message', messageHandler);

    setInitialOutput();
    wrapper.append(toolbar, sources, inputPanel, frame, output);

    return wrapper;
};
