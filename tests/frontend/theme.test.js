import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../../app/static/js/theme.js', import.meta.url), 'utf8');
const storageKey = 'musa_code_academy_theme';

const setup = ({ saved = null, dark = false, unavailable = false } = {}) => {
    const listeners = { document: new Map(), window: new Map(), system: new Map() };
    const picker = { value: 'system', matches: (selector) => selector === '[data-theme-picker]' };
    const themeMeta = { content: '#f7f8f2' };
    const schemeMeta = { content: 'light' };
    const document = {
        documentElement: { dataset: {} },
        querySelectorAll: (selector) => ({
            '[data-theme-picker]': [picker],
            'meta[name="theme-color"]': [themeMeta],
            'meta[name="color-scheme"]': [schemeMeta],
        })[selector] ?? [],
        addEventListener: (type, listener) => listeners.document.set(type, listener),
    };
    const system = { matches: dark, addEventListener: (type, listener) => listeners.system.set(type, listener) };
    const storage = new Map(saved === null ? [] : [[storageKey, saved]]);
    const events = [];
    const window = {
        matchMedia: () => system,
        addEventListener: (type, listener) => listeners.window.set(type, listener),
        dispatchEvent: (event) => events.push(event),
    };
    vm.runInNewContext(source, {
        document, window,
        CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
        localStorage: {
            getItem(key) { if (unavailable) throw new Error('denied'); return storage.get(key) ?? null; },
            setItem(key, value) { if (unavailable) throw new Error('denied'); storage.set(key, value); },
        },
    });
    return {
        document, picker, storage, themeMeta, schemeMeta, events,
        theme: () => document.documentElement.dataset.theme,
        ready: () => listeners.document.get('DOMContentLoaded')(),
        select(value) { picker.value = value; listeners.document.get('change')({ target: picker }); },
        systemChange(dark) { system.matches = dark; listeners.system.get('change')(); },
        storageChange(value, key = storageKey) { listeners.window.get('storage')({ key, newValue: value }); },
    };
};

test('applies the saved theme before DOMContentLoaded, even when the system differs', () => {
    const page = setup({ saved: 'dark' });
    assert.equal(page.theme(), 'dark');
    assert.equal(page.themeMeta.content, '#171c16');
    assert.equal(page.schemeMeta.content, 'dark');
    page.ready();
    assert.equal(page.picker.value, 'dark');
});

test('follows live system changes until an explicit theme is selected', () => {
    const page = setup({ dark: true });
    assert.equal(page.theme(), 'dark');
    assert.equal(page.picker.value, 'system');
    page.systemChange(false);
    assert.equal(page.theme(), 'light');
    page.select('dark');
    page.systemChange(false);
    assert.equal(page.theme(), 'dark');
    assert.equal(page.storage.get(storageKey), 'dark');
    page.select('system');
    assert.equal(page.theme(), 'light');
    page.systemChange(true);
    assert.equal(page.theme(), 'dark');
});

test('notifies mounted editors and synchronizes the selector', () => {
    const page = setup();
    page.select('dark');
    const event = page.events.at(-1);
    assert.equal(event.type, 'academy:theme-change');
    assert.equal(event.detail.theme, 'dark');
    assert.equal(event.detail.preference, 'dark');
    assert.equal(page.picker.value, 'dark');
});

test('synchronizes changes from another tab, including removing the saved preference', () => {
    const page = setup({ saved: 'light', dark: true });
    page.storageChange('dark');
    assert.equal(page.theme(), 'dark');
    page.storageChange('light', 'unrelated');
    assert.equal(page.theme(), 'dark');
    page.storageChange(null);
    assert.equal(page.picker.value, 'system');
    page.systemChange(false);
    assert.equal(page.theme(), 'light');
    page.select('dark');
    page.storageChange(null, null);
    assert.equal(page.theme(), 'light');
});

test('falls back to the system for invalid preferences', () => {
    const page = setup({ saved: 'unknown', dark: true });
    assert.equal(page.theme(), 'dark');
    assert.equal(page.picker.value, 'system');
});

test('supports switching themes when browser storage is blocked', () => {
    const page = setup({ unavailable: true });
    page.select('dark');
    assert.equal(page.theme(), 'dark');
    page.select('light');
    assert.equal(page.theme(), 'light');
});
