import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../../app/static/js/theme.js', import.meta.url), 'utf8');
const storageKey = 'musa_code_academy_theme';

const setup = ({ saved = null, dark = false, unavailable = false } = {}) => {
    const listeners = { document: new Map(), window: new Map(), system: new Map() };
    const picker = {
        attributes: new Map(),
        setAttribute(name, value) { this.attributes.set(name, value); },
        closest: (selector) => selector === '[data-theme-picker]' ? picker : null,
    };
    const themeMeta = { content: '#f7f8f2' };
    const schemeMeta = { content: 'light' };
    const icon = { href: '/static/images/mca-icon-light.png', dataset: {
        lightHref: '/static/images/mca-icon-light.png', darkHref: '/static/images/mca-icon-dark.png',
    } };
    const document = {
        documentElement: { dataset: {} },
        querySelectorAll: (selector) => ({
            '[data-theme-picker]': [picker],
            'meta[name="theme-color"]': [themeMeta],
            'meta[name="color-scheme"]': [schemeMeta],
            '[data-theme-icon]': [icon],
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
        document, picker, storage, themeMeta, schemeMeta, icon, events,
        theme: () => document.documentElement.dataset.theme,
        ready: () => listeners.document.get('DOMContentLoaded')(),
        click(target = picker) { listeners.document.get('click')({ target }); },
        systemChange(dark) { system.matches = dark; listeners.system.get('change')(); },
        storageChange(value, key = storageKey) { listeners.window.get('storage')({ key, newValue: value }); },
    };
};

test('applies the saved theme before DOMContentLoaded, even when the system differs', () => {
    const page = setup({ saved: 'dark' });
    assert.equal(page.theme(), 'dark');
    assert.equal(page.themeMeta.content, '#151923');
    assert.equal(page.schemeMeta.content, 'dark');
    page.ready();
    assert.equal(page.picker.attributes.get('aria-label'), 'Включить светлую тему');
});

test('follows the system until a click selects the opposite theme', () => {
    const page = setup({ dark: true });
    assert.equal(page.theme(), 'dark');
    assert.equal(page.picker.attributes.get('aria-label'), 'Включить светлую тему');
    page.systemChange(false);
    assert.equal(page.theme(), 'light');
    page.click();
    page.systemChange(false);
    assert.equal(page.theme(), 'dark');
    assert.equal(page.storage.get(storageKey), 'dark');
    page.storageChange(null);
    assert.equal(page.theme(), 'light');
    page.systemChange(true);
    assert.equal(page.theme(), 'dark');
});

test('clicking the SVG notifies mounted editors and updates the accessible button label', () => {
    const page = setup();
    page.click({ closest: () => page.picker });
    const event = page.events.at(-1);
    assert.equal(event.type, 'academy:theme-change');
    assert.equal(event.detail.theme, 'dark');
    assert.equal(event.detail.preference, 'dark');
    assert.equal(page.picker.attributes.get('aria-label'), 'Включить светлую тему');
});

test('synchronizes changes from another tab, including removing the saved preference', () => {
    const page = setup({ saved: 'light', dark: true });
    page.storageChange('dark');
    assert.equal(page.theme(), 'dark');
    page.storageChange('light', 'unrelated');
    assert.equal(page.theme(), 'dark');
    page.storageChange(null);
    assert.equal(page.picker.attributes.get('aria-label'), 'Включить светлую тему');
    page.systemChange(false);
    assert.equal(page.theme(), 'light');
    page.click();
    page.storageChange(null, null);
    assert.equal(page.theme(), 'light');
});

test('falls back to the system for invalid preferences', () => {
    const page = setup({ saved: 'unknown', dark: true });
    assert.equal(page.theme(), 'dark');
    assert.equal(page.picker.attributes.get('aria-label'), 'Включить светлую тему');
});

test('supports switching themes when browser storage is blocked', () => {
    const page = setup({ unavailable: true });
    page.click();
    assert.equal(page.theme(), 'dark');
    page.click();
    assert.equal(page.theme(), 'light');
    assert.equal(page.picker.attributes.get('aria-label'), 'Включить тёмную тему');
    assert.equal(page.picker.title, 'Включить тёмную тему');
});

test('switches the favicon and browser color with the selected and system themes', () => {
    const page = setup();
    assert.equal(page.icon.href, '/static/images/mca-icon-light.png');
    assert.equal(page.themeMeta.content, '#fcfdff');
    page.click();
    assert.equal(page.icon.href, '/static/images/mca-icon-dark.png');
    assert.equal(page.themeMeta.content, '#151923');
    page.click();
    assert.equal(page.icon.href, '/static/images/mca-icon-light.png');
    page.storageChange(null);
    page.systemChange(true);
    assert.equal(page.icon.href, '/static/images/mca-icon-dark.png');
});
