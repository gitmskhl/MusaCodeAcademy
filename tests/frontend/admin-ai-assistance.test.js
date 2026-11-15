import test from 'node:test';
import assert from 'node:assert/strict';
import { createAIAssistanceSettings } from '../../app/static/js/admin-ai-assistance.js';

const flush = () => new Promise(resolve => setImmediate(resolve));

class Element {
    constructor(tag) {
        this.tag = tag;
        this.children = [];
        this.handlers = {};
        this.attributes = {};
        this.disabled = false;
        this.hidden = false;
        this.classList = { toggle() {} };
    }
    append(...children) { children.forEach(child => { child.parent = this; this.children.push(child); }); }
    replaceChildren(...children) { this.children = []; this.append(...children); }
    remove() { this.parent.children = this.parent.children.filter(child => child !== this); }
    setAttribute(name, value) { this.attributes[name] = value; }
    addEventListener(name, callback) { this.handlers[name] = callback; }
    reportValidity() { return true; }
    querySelectorAll(selector) {
        const tags = selector.split(',').map(value => value.trim());
        return this.children.flatMap(child => [...(tags.includes(child.tag) ? [child] : []), ...child.querySelectorAll(selector)]);
    }
}

function setup({ enabled = true, models = ['vendor/mini', 'vendor/flash', 'vendor/oss'] } = {}) {
    globalThis.document = {
        createElement: tag => new Element(tag),
        createTextNode: text => Object.assign(new Element('#text'), { textContent: text }),
    };
    const user = { id: 7, ai_assistance_enabled: enabled, ai_daily_limit: 10, ai_model_limits: null };
    const requests = [];
    const notices = [];
    const state = { fail: false };
    const element = createAIAssistanceSettings({ user, onSaved: message => notices.push(message), api: async (url, options) => {
        requests.push({ url, options });
        if (!options) return models;
        if (state.fail) throw new Error('Ошибка сохранения.');
        const payload = JSON.parse(options.body);
        return { ...user, ai_assistance_enabled: payload.enabled,
            ai_daily_limit: payload.daily_limit ?? user.ai_daily_limit,
            ai_model_limits: payload.model_limits ?? user.ai_model_limits };
    } });
    const [caption, form, error] = element.children;
    const toggle = caption.children[0];
    const [dailyLabel, , rowsHost, add, total, save] = form.children;
    const daily = dailyLabel.children[0];
    const row = index => {
        const [modelLabel, countLabel, remove] = rowsHost.children[index].children;
        return { select: modelLabel.children[0], count: countLabel.children[0], remove };
    };
    const submit = () => form.handlers.submit({ preventDefault() {} });
    return { user, requests, notices, state, toggle, form, error, daily, rowsHost, add, total, save, row, submit };
}

test('shows detailed settings after enabling AI assistance and hides them after disabling', async () => {
    const page = setup({ enabled: false });
    await flush();
    assert.equal(page.form.hidden, true);
    page.toggle.checked = true;
    await page.toggle.handlers.change();
    assert.equal(page.form.hidden, false);
    assert.equal(page.user.ai_assistance_enabled, true);
    assert.equal(page.rowsHost.children.length, 1);
    page.toggle.checked = false;
    await page.toggle.handlers.change();
    assert.equal(page.form.hidden, true);
});

test('saves the daily budget split as 1 + 2 + 1 among three models', async () => {
    const page = setup();
    await flush();
    page.daily.value = 4;
    page.row(0).count.value = 1;
    page.add.handlers.click();
    page.row(1).count.value = 2;
    page.add.handlers.click();
    assert.equal(page.rowsHost.children.length, 3);
    assert.equal(page.add.disabled, true);
    await page.submit();
    assert.deepEqual(JSON.parse(page.requests.at(-1).options.body), {
        enabled: true, daily_limit: 4,
        model_limits: { 'vendor/mini': 1, 'vendor/flash': 2, 'vendor/oss': 1 },
    });
    assert.equal(page.user.ai_daily_limit, 4);
    assert.equal(page.error.hidden, true);
    assert.equal(page.notices.at(-1), 'Настройки AI-помощи сохранены.');
});

test('rejects mismatched totals and duplicate models without submitting', async () => {
    const page = setup();
    await flush();
    page.daily.value = 4;
    await page.submit();
    assert.match(page.error.textContent, /Сумма запросов/);
    assert.equal(page.requests.length, 1);
    page.row(0).count.value = 2;
    page.add.handlers.click();
    page.row(1).count.value = 2;
    page.row(1).select.value = 'vendor/mini';
    await page.submit();
    assert.match(page.error.textContent, /только один раз/);
    assert.equal(page.requests.length, 1);
    page.row(1).remove.handlers.click();
    assert.equal(page.rowsHost.children.length, 1);
});

test('keeps edited settings after a save error and reverts a failed toggle', async () => {
    const page = setup();
    await flush();
    page.state.fail = true;
    page.daily.value = 4;
    page.row(0).count.value = 4;
    await page.submit();
    assert.equal(page.daily.value, 4);
    assert.equal(page.row(0).count.value, 4);
    assert.equal(page.user.ai_daily_limit, 10);
    assert.equal(page.save.disabled, false);
    assert.match(page.error.textContent, /Ошибка сохранения/);
    page.toggle.checked = false;
    await page.toggle.handlers.change();
    assert.equal(page.toggle.checked, true);
    assert.equal(page.form.hidden, false);
});

test('explains missing model configuration and disables saving', async () => {
    const page = setup({ models: [] });
    await flush();
    assert.match(page.error.textContent, /AI_MODEL_1/);
    assert.equal(page.save.disabled, true);
    assert.equal(page.add.disabled, true);
});
