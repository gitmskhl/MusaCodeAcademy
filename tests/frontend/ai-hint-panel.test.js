import test from 'node:test';
import assert from 'node:assert/strict';
import { createAIHintPanel } from '../../app/static/js/task-viewer/ai-hint-panel.js';

const flush = () => new Promise(resolve => setImmediate(resolve));
const status = (overrides = {}) => ({
    enabled: true, daily_limit: 10, remaining: 10,
    models: [{ model: 'vendor/test-model', daily_limit: 10, remaining: 10 }],
    resets_at: new Date(Date.now() + 86_400_000).toISOString(), ...overrides,
});
const failed = (id = 1, overrides = {}) => ({ id, status: 'WRONG ANSWER', ai_hint: null, ...overrides });
const response = (body, code = 200) => ({ ok: code < 400, status: code, json: async () => body });

function setup({ availability = status(), hint = response({ ...status({ remaining: 9 }), hint: 'Проверь тип данных.' }) } = {}) {
    const timers = new Map();
    const requests = [];
    const controller = new AbortController();
    globalThis.document = { createElement(tag) {
        return {
            tag, hidden: false, disabled: false, textContent: '', attributes: {}, children: [], handlers: {},
            classes: new Set(),
            classList: { toggle(name, value) { if (value) this.owner.classes.add(name); else this.owner.classes.delete(name); } },
            append(...nodes) { this.children.push(...nodes); },
            replaceChildren(...nodes) { this.children = nodes; },
            setAttribute(name, value) { this.attributes[name] = value; },
            addEventListener(name, handler) { this.handlers[name] = handler; },
        };
    } };
    const createElement = document.createElement;
    document.createElement = tag => {
        const node = createElement(tag);
        node.classList.owner = node;
        return node;
    };
    globalThis.window = {
        setTimeout(handler) { const key = timers.size + 1; timers.set(key, handler); return key; },
        clearTimeout(key) { timers.delete(key); },
    };
    const state = { availability, hint, statusFailure: false };
    const panel = createAIHintPanel({ signal: controller.signal, fetcher: async (url, options) => {
        requests.push({ url, options });
        if (url.endsWith('/status')) {
            if (state.statusFailure) throw new TypeError('Failed to fetch');
            return response(state.availability);
        }
        if (state.hint instanceof Error) throw state.hint;
        return await state.hint;
    } });
    const [header, quota, modelLabel, message] = panel.element.children;
    const select = modelLabel.children[1];
    const button = header.children[1];
    return { panel, button, quota, select, message, requests, state, timers, controller };
}

test('shows hints only for enabled users with an unsuccessful submission', async () => {
    const page = setup({ availability: status({ enabled: false }) });
    page.panel.render(failed());
    assert.equal(page.panel.element.hidden, true);
    await flush();
    assert.equal(page.panel.element.hidden, true);
    page.state.availability = status();
    page.panel.render(failed(2));
    await flush();
    assert.equal(page.panel.element.hidden, false);
    for (const state of ['PENDING', 'RUNNING', 'ACCEPTED', 'SYSTEM_ERROR', 'FAILED']) {
        page.panel.render(failed(2, { status: state }));
        assert.equal(page.panel.element.hidden, true);
    }
    for (const state of ['WRONG ANSWER', 'RUNTIME_ERROR', 'COMPILATION_ERROR', 'TIME_LIMIT_EXCEEDED', 'MEMORY_LIMIT_EXCEEDED']) {
        page.panel.render(failed(2, { status: state }));
        assert.equal(page.panel.element.hidden, false);
    }
});

test('posts only the saved submission ID, displays plain text, and prevents repeat clicks', async () => {
    let finish;
    const page = setup({ hint: new Promise(resolve => { finish = resolve; }) });
    page.panel.render(failed(42));
    await flush();
    const pending = page.button.handlers.click();
    assert.equal(page.button.disabled, true);
    await page.button.handlers.click();
    assert.equal(page.requests.filter(request => request.url.endsWith('/hint')).length, 1);
    const request = page.requests.at(-1);
    assert.equal(request.url, '/api/submissions/42/hint');
    assert.equal(request.options.method, 'POST');
    assert.deepEqual(JSON.parse(request.options.body), { model: 'vendor/test-model' });
    const hint = '<script>alert(1)</script> Проверь input().';
    finish(response({ ...status({ remaining: 9 }), hint }));
    await pending;
    assert.equal(page.message.textContent, hint);
    assert.equal(page.message.children.length, 0);
    assert.equal(page.button.hidden, true);
    assert.match(page.quota.textContent, /9 из 10/);
    page.panel.render(failed(42));
    assert.equal(page.message.textContent, hint);
});

test('restores a saved hint without requesting generation', async () => {
    const page = setup({ availability: status({ remaining: 0 }) });
    page.panel.render(failed(1, { ai_hint: 'Сохранённый совет.' }));
    await flush();
    assert.equal(page.message.textContent, 'Сохранённый совет.');
    assert.equal(page.button.hidden, true);
    assert.equal(page.requests.length, 1);
});

test('shows provider and network errors and allows retry', async () => {
    for (const hint of [response({ detail: 'Сервис AI перегружен.' }, 503), new TypeError('Failed to fetch')]) {
        const page = setup({ hint });
        page.panel.render(failed());
        await flush();
        await page.button.handlers.click();
        assert.equal(page.button.disabled, false);
        assert.equal(page.message.attributes.role, 'alert');
        assert.ok(page.message.textContent);
        page.state.hint = response({ ...status({ remaining: 9 }), hint: 'Попробуй проверить тип.' });
        await page.button.handlers.click();
        assert.equal(page.message.textContent, 'Попробуй проверить тип.');
        assert.equal(page.message.attributes.role, 'status');
    }
});

test('refreshes an exhausted quota at the next calendar day', async () => {
    const page = setup({ hint: response({ detail: 'Лимит исчерпан.' }, 429) });
    page.panel.render(failed());
    await flush();
    page.state.availability = status({ remaining: 0 });
    await page.button.handlers.click();
    assert.equal(page.button.disabled, true);
    assert.match(page.quota.textContent, /0 из 10/);
    page.state.availability = status();
    const timer = [...page.timers.values()][0];
    timer();
    await flush();
    assert.equal(page.button.disabled, false);
    assert.match(page.quota.textContent, /10 из 10/);
    assert.doesNotMatch(page.message.textContent, /исчерпан/);
});

test('ignores a late AI response after switching to another submission', async () => {
    let finish;
    const page = setup({ hint: new Promise(resolve => { finish = resolve; }) });
    page.panel.render(failed(1));
    await flush();
    const pending = page.button.handlers.click();
    page.panel.render(failed(2));
    await flush();
    finish(response({ ...status({ remaining: 9 }), hint: 'Подсказка к первой отправке.' }));
    await pending;
    assert.notEqual(page.message.textContent, 'Подсказка к первой отправке.');
    assert.equal(page.button.hidden, false);
    page.panel.setBusy(true);
    assert.equal(page.button.disabled, true);
    page.panel.setBusy(false);
    assert.equal(page.button.disabled, false);
});

test('retries checking access without immediately generating a paid hint', async () => {
    const page = setup();
    page.state.statusFailure = true;
    page.panel.render(failed());
    await flush();
    assert.match(page.button.textContent, /Повторить проверку/);
    page.state.statusFailure = false;
    await page.button.handlers.click();
    assert.equal(page.requests.length, 2);
    assert.ok(page.requests.every(request => request.url.endsWith('/status')));
    assert.equal(page.button.textContent, 'Подсказка');
});

test('clears the daily refresh timer when leaving the page', async () => {
    const page = setup();
    page.panel.render(failed());
    await flush();
    assert.equal(page.timers.size, 1);
    page.controller.abort();
    assert.equal(page.timers.size, 0);
});

test('selects among allowed models and sends the selected model to the server', async () => {
    const page = setup({ availability: status({ daily_limit: 4, remaining: 4, models: [
        { model: 'vendor/mini', daily_limit: 1, remaining: 1 },
        { model: 'vendor/flash', daily_limit: 3, remaining: 3 },
    ] }) });
    page.panel.render(failed());
    await flush();
    assert.equal(page.select.children.length, 2);
    assert.equal(page.select.value, 'vendor/mini');
    page.select.value = 'vendor/flash';
    page.select.handlers.change();
    await page.button.handlers.click();
    assert.deepEqual(JSON.parse(page.requests.at(-1).options.body), { model: 'vendor/flash' });
});

test('exhausting one model leaves other model budgets usable', async () => {
    const models = [
        { model: 'vendor/mini', daily_limit: 1, remaining: 1 },
        { model: 'vendor/flash', daily_limit: 3, remaining: 3 },
    ];
    const page = setup({ availability: status({ daily_limit: 4, remaining: 4, models }),
        hint: response({ detail: 'Лимит выбранной модели исчерпан.' }, 429) });
    page.panel.render(failed());
    await flush();
    page.state.availability = status({ daily_limit: 4, remaining: 3, models: [
        { ...models[0], remaining: 0 }, models[1],
    ] });
    await page.button.handlers.click();
    assert.match(page.quota.textContent, /3 из 4/);
    assert.equal(page.select.children[0].disabled, true);
    assert.equal(page.button.disabled, true);
    page.select.value = 'vendor/flash';
    page.select.handlers.change();
    assert.equal(page.button.disabled, false);
    assert.doesNotMatch(page.message.textContent, /исчерпан/);
});

test('does not offer a request when no model is allocated', async () => {
    const page = setup({ availability: status({ models: [] }) });
    page.panel.render(failed());
    await flush();
    assert.equal(page.button.disabled, true);
    assert.match(page.message.textContent, /модели пока не настроены/);
});
