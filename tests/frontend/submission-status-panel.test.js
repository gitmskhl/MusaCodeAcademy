import test from 'node:test';
import assert from 'node:assert/strict';
import { createSubmissionStatusPanel } from '../../app/static/js/task-viewer/submission-status-panel.js';

function setup() {
    globalThis.document = { createElement(tag) {
        return {
            tag, textContent: '', className: '', children: [], dataset: {}, style: {},
            classList: { add() {}, remove() {} },
            append(...nodes) { this.children.push(...nodes); },
            replaceChildren(...nodes) { this.children = nodes; },
            setAttribute() {}, addEventListener() {},
        };
    } };
    const panel = createSubmissionStatusPanel({ fetcher: async () => {
        throw new Error('Rendering hints must not fetch test details');
    } });
    const nodes = (node) => [node, ...node.children.flatMap(nodes)];
    return { panel, nodes: () => nodes(panel.element) };
}

const failed = (diagnostics = []) => ({
    status: 'WRONG ANSWER', passed_tests: 0, total_tests: 1,
    actual_output: 'hello  world', failed_test_id: 1, diagnostics,
});

test('renders multiple hints as text inside the existing result card', () => {
    const page = setup();
    page.panel.render(failed([
        { type: 'case_mismatch', message: 'Проверьте регистр.' },
        { type: 'extra_whitespace', message: '<script>пробелы</script>' },
        { type: 'case_mismatch', message: 'Проверьте регистр.' },
    ]));
    const texts = page.nodes().map(node => node.textContent);
    assert.equal(texts.filter(text => text === '💡 Подсказка').length, 1);
    assert.equal(texts.filter(text => text === 'Проверьте регистр.').length, 1);
    assert.ok(texts.includes('<script>пробелы</script>'));
    assert.ok(texts.includes('Неверный ответ'));
    assert.ok(texts.includes('hello  world'));
    assert.ok(texts.includes('Показать непройденный тест'));
    assert.ok(page.nodes().every(node => node.tag !== 'script'));
});

test('omits the hint section when diagnostics are absent, empty or unusable', () => {
    for (const diagnostics of [undefined, [], null, [{ message: ' ' }], [null]]) {
        const page = setup();
        page.panel.render(failed(diagnostics));
        assert.ok(!page.nodes().some(node => node.textContent === '💡 Подсказка'));
    }
});

test('never renders diagnostics for another verdict', () => {
    const page = setup();
    for (const status of ['ACCEPTED', 'PENDING', 'RUNNING', 'RUNTIME_ERROR',
        'TIME_LIMIT_EXCEEDED', 'MEMORY_LIMIT_EXCEEDED', 'SYSTEM_ERROR']) {
        page.panel.render({ ...failed([{ message: 'Do not show' }]), status });
        assert.ok(!page.nodes().some(node => node.textContent === '💡 Подсказка'));
    }
});

test('updates hints when only diagnostics change and removes stale hints', () => {
    const page = setup();
    page.panel.render(failed());
    page.panel.render(failed([{ message: 'New hint' }]));
    assert.ok(page.nodes().some(node => node.textContent === 'New hint'));
    page.panel.render(failed());
    assert.ok(!page.nodes().some(node => node.textContent === 'New hint'));
});
