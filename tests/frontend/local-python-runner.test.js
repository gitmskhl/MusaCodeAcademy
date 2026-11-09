import test from 'node:test';
import assert from 'node:assert/strict';
import { runLocalPythonTests } from '../../app/static/js/task-viewer/local-python-runner.js';

class FakeWorker {
    static instances = [];
    static handler = () => {};
    constructor() {
        this.messages = [];
        this.terminated = false;
        FakeWorker.instances.push(this);
    }
    postMessage(message) {
        this.messages.push(message);
        queueMicrotask(() => FakeWorker.handler(message, this));
    }
    emit(data) { this.onmessage({ data }); }
    terminate() { this.terminated = true; }
}

const bundle = {
    time_limit_ms: 10,
    test_cases: [
        { id: 10, input: '2', expected_output: '4' },
        { id: 20, input: '3', expected_output: '6' },
    ],
};

const setup = (t, handler) => {
    t.mock.method(globalThis, 'Worker', FakeWorker);
    FakeWorker.instances = [];
    FakeWorker.handler = handler;
};
// Node has no browser Worker global to mock until it is declared.
if (!globalThis.Worker) globalThis.Worker = FakeWorker;

const run = (options = {}) => runLocalPythonTests({ sourceCode: 'print(4)', testBundle: bundle, ...options });

test('passes all tests in order and releases the worker', async (t) => {
    setup(t, (message, worker) => {
        if (message.type === 'init') worker.emit({ type: 'ready' });
        else worker.emit({ type: 'result', result: { status: 'ACCEPTED' }, execution_time_ms: 2 });
    });
    const result = await run();
    assert.equal(result.status, 'ACCEPTED');
    assert.equal(result.passed_tests, 2);
    assert.equal(result.failed_test_id, null);
    assert.equal(result.execution_time_ms, 4);
    const worker = FakeWorker.instances[0];
    assert.deepEqual(worker.messages.filter(m => m.type === 'run').map(m => m.test.id), [10, 20]);
    assert.equal(worker.terminated, true);
});

test('stops on the first failure and preserves output and passed count', async (t) => {
    setup(t, (message, worker) => {
        if (message.type === 'init') worker.emit({ type: 'ready' });
        else worker.emit({
            type: 'result', execution_time_ms: 1,
            result: message.test.id === 10 ? { status: 'ACCEPTED' } : { status: 'WRONG ANSWER', actual_output: '4' },
        });
    });
    const result = await run();
    assert.equal(result.status, 'WRONG ANSWER');
    assert.equal(result.passed_tests, 1);
    assert.equal(result.failed_test_id, 20);
    assert.equal(result.actual_output, '4');
});

test('terminates a hung Python test at its deadline', async (t) => {
    setup(t, (message, worker) => {
        if (message.type === 'init') worker.emit({ type: 'ready' });
    });
    const result = await run();
    assert.equal(result.status, 'TIME_LIMIT_EXCEEDED');
    assert.equal(result.failed_test_id, 10);
    assert.equal(FakeWorker.instances[0].terminated, true);
});

test('aborting on navigation terminates the worker and rejects the pending run', async (t) => {
    setup(t, () => {});
    const controller = new AbortController();
    const pending = run({ signal: controller.signal });
    controller.abort();
    await assert.rejects(pending, { name: 'AbortError' });
    assert.equal(FakeWorker.instances[0].terminated, true);
});

test('runtime download errors reject rather than creating a passing result', async (t) => {
    setup(t, (message, worker) => worker.emit({ type: 'error', message: 'CDN unavailable' }));
    await assert.rejects(run(), /CDN unavailable/);
    assert.equal(FakeWorker.instances[0].terminated, true);
});

test('initialization has a separate deadline and is not reported as a student timeout', async (t) => {
    setup(t, () => {});
    t.mock.timers.enable({ apis: ['setTimeout'] });
    const pending = run();
    const assertion = assert.rejects(pending, /Подготовка к проверке/);
    t.mock.timers.tick(120_000);
    await assertion;
    assert.equal(FakeWorker.instances[0].terminated, true);
});

test('tasks without tests cannot pass', async (t) => {
    setup(t, () => {});
    await assert.rejects(run({ testBundle: { ...bundle, test_cases: [] } }), /не добавлены тесты/);
    assert.equal(FakeWorker.instances.length, 0);
});
