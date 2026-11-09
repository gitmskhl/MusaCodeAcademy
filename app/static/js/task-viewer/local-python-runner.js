const INITIALIZATION_TIMEOUT_MS = 120_000;

export const runLocalPythonTests = ({ sourceCode, testBundle, signal, onProgress }) => {
    const tests = testBundle.test_cases;
    if (!tests?.length) return Promise.reject(new Error('Для задачи ещё не добавлены тесты.'));
    if (signal?.aborted) return Promise.reject(new DOMException('Проверка отменена', 'AbortError'));

    return new Promise((resolve, reject) => {
        const worker = new Worker(new URL('./local-python-worker.js', import.meta.url));
        let timer;
        let passedTests = 0;
        let executionTime = 0;
        let finished = false;

        const finish = (result, error) => {
            if (finished) return;
            finished = true;
            clearTimeout(timer);
            worker.terminate();
            signal?.removeEventListener('abort', abort);
            if (error) reject(error);
            else resolve(result);
        };
        const abort = () => finish(null, new DOMException('Проверка отменена', 'AbortError'));

        const buildResult = (status, actualOutput = null) => ({
            status,
            passed_tests: passedTests,
            total_tests: tests.length,
            failed_test_id: status === 'ACCEPTED' ? null : tests[passedTests].id,
            actual_output: status === 'ACCEPTED' ? null : actualOutput,
            execution_time_ms: executionTime,
        });

        const runNextTest = () => {
            onProgress?.(`Проверяем решение: тест ${passedTests + 1} из ${tests.length}…`);
            // Arm the deadline before starting Python, so even an infinite loop
            // can be stopped by terminating the worker from the UI thread.
            timer = setTimeout(() => {
                executionTime += testBundle.time_limit_ms;
                finish(buildResult('TIME_LIMIT_EXCEEDED'));
            }, testBundle.time_limit_ms);
            worker.postMessage({ type: 'run', sourceCode, test: tests[passedTests] });
        };

        worker.onmessage = ({ data }) => {
            if (finished) return;
            clearTimeout(timer);
            if (data.type === 'ready') {
                runNextTest();
            } else if (data.type === 'result') {
                executionTime += data.execution_time_ms;
                if (data.result.status !== 'ACCEPTED') {
                    finish(buildResult(data.result.status, data.result.actual_output));
                } else if (++passedTests === tests.length) {
                    finish(buildResult('ACCEPTED'));
                } else {
                    runNextTest();
                }
            } else if (data.type === 'error') {
                finish(null, new Error(data.message || 'Не удалось проверить решение.'));
            }
        };
        worker.onerror = (event) => {
            event.preventDefault();
            finish(null, new Error('Не удалось начать проверку. Проверьте подключение и повторите попытку.'));
        };
        worker.onmessageerror = () => finish(null, new Error('Не удалось получить результат проверки.'));
        signal?.addEventListener('abort', abort, { once: true });
        timer = setTimeout(() => finish(null, new Error(
            'Подготовка к проверке заняла слишком много времени. Проверьте подключение и повторите попытку.'
        )), INITIALIZATION_TIMEOUT_MS);
        onProgress?.('Подготавливаем проверку решения. Первый запуск может занять некоторое время…');
        worker.postMessage({ type: 'init' });
    });
};
