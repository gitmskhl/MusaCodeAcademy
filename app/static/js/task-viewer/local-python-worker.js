// Classic worker: importScripts loads the pinned Pyodide runtime from the CDN.
const PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/';
let pyodide;
let checkTest;

self.onmessage = async ({ data }) => {
    try {
        if (data.type === 'init') {
            const harnessResponse = await fetch('./local-python-checker.py');
            if (!harnessResponse.ok) throw new Error('Не удалось загрузить модуль проверки.');
            const harness = await harnessResponse.text();
            importScripts(`${PYODIDE_URL}pyodide.js`);
            pyodide = await loadPyodide({ indexURL: PYODIDE_URL });
            pyodide.runPython(harness);
            checkTest = pyodide.globals.get('check_python_test');
            self.postMessage({ type: 'ready' });
        } else if (data.type === 'run') {
            const started = performance.now();
            const result = JSON.parse(checkTest(
                data.sourceCode, data.test.input ?? '', data.test.expected_output
            ));
            self.postMessage({
                type: 'result', result,
                execution_time_ms: Math.round(performance.now() - started),
            });
        }
    } catch (error) {
        self.postMessage({ type: 'error', message: error.message });
    }
};
