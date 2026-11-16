import test from 'node:test';
import assert from 'node:assert/strict';
import { safeNextUrl } from '../../app/static/js/safe-next.js';
import { homeworkLink, notificationCard } from '../../app/static/js/notifications.js';
import { authFetch } from '../../app/static/js/course-auth.js';

class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.handlers = {}; this.classes = new Set(); this.classList = { toggle: (name, value) => value ? this.classes.add(name) : this.classes.delete(name) }; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    setAttribute(name, value) { this[name] = value; }
    addEventListener(type, handler) { this.handlers[type] = handler; }
}
function setup() {
    const requests = [];
    const events = [];
    const destinations = [];
    globalThis.document = { createElement: tag => new Element(tag), dispatchEvent: event => events.push(event.type) };
    globalThis.localStorage = { getItem: () => 'token' };
    globalThis.window = { location: { origin: 'https://mca.example', assign: url => destinations.push(url) } };
    globalThis.fetch = async (url, init) => {
        requests.push({ url, init });
        return { ok: true, status: 200, json: async () => ({ read_at: '2026-11-16T12:00:00Z' }) };
    };
    return { requests, events, destinations };
}
const item = () => ({ id: 12, title: '<script>Домашняя работа</script>', text: '<b>Комментарий</b>', created_at: '2026-11-16T10:00:00Z', read_at: null, homework: null });

test('rendering notifications never marks them read and keeps text as textContent', () => {
    const page = setup();
    const card = notificationCard(item());
    assert.equal(page.requests.length, 0);
    assert.equal(card.classes.has('is-unread'), true);
    assert.equal(card.children[0].children[0].textContent, '<script>Домашняя работа</script>');
    assert.equal(card.children.at(-1).textContent, '<b>Комментарий</b>');
});

test('clicking a notification reads it once and refreshes the count', async () => {
    const page = setup();
    const card = notificationCard(item());
    card.handlers.click({ target: { closest: () => null } });
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(page.requests.length, 1);
    assert.equal(page.requests[0].url, '/api/notifications/12/read');
    assert.equal(card.classes.has('is-unread'), false);
    assert.deepEqual(page.events, ['notifications-changed']);
    card.handlers.click({ target: { closest: () => null } });
    assert.equal(page.requests.length, 1);
});

test('homework opens the exact URL after marking its notification read', async () => {
    const page = setup();
    const homework = { url: '/python/steps/42?task=7#editor' };
    let read = false;
    const link = homeworkLink(homework, async next => { assert.equal(next, homework.url); read = true; }, assert.fail);
    assert.equal(link.href, homework.url);
    let prevented = false;
    await link.handlers.click({ type: 'click', preventDefault() { prevented = true; } });
    assert.equal(prevented, true);
    assert.equal(read, true);
    assert.deepEqual(page.destinations, [homework.url]);
});

test('the homework button in a notification persists its read status before navigation', async () => {
    const page = setup();
    const homework = { url: '/python/steps/42', comment: 'Практика' };
    const card = notificationCard({ ...item(), homework });
    const open = card.children.at(-1);
    assert.equal(page.requests.length, 0);
    await open.handlers.click({ type: 'click', preventDefault() {} });
    assert.equal(page.requests[0].url, '/api/notifications/12/read');
    assert.equal(page.requests[0].init.method, 'POST');
    assert.equal(card.classes.has('is-unread'), false);
    assert.deepEqual(page.destinations, [homework.url]);
    assert.deepEqual(page.events, ['notifications-changed']);
});

test('the bell shows ten notifications while its counter includes all unread notifications', async () => {
    const page = setup();
    const nodes = new Map();
    const bell = new Element('div');
    bell.querySelector = selector => {
        if (!nodes.has(selector)) nodes.set(selector, new Element('div'));
        return nodes.get(selector);
    };
    globalThis.document.querySelector = () => bell;
    globalThis.document.addEventListener = () => {};
    globalThis.fetch = async (url, init) => {
        page.requests.push({ url, init });
        const size = Number(new URL(url, window.location.origin).searchParams.get('page_size'));
        return { ok: true, status: 200, json: async () => ({ items: Array.from({ length: Math.min(size, 15) }, (_, i) => ({ ...item(), id: i + 1 })), unread_count: 15 }) };
    };
    await import('../../app/static/js/notification-bell.js');
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(nodes.get('[data-notification-latest]').children.length, 10);
    assert.equal(nodes.get('[data-notification-count]').textContent, '15');
    nodes.get('[data-notification-toggle]').handlers.click();
    assert.equal(page.requests.length, 1);
    assert.ok(page.requests.every(request => !request.init.method || request.init.method === 'GET'));
});

test('opening homework in a new tab retains native link navigation and records the read', async () => {
    const page = setup();
    let reads = 0;
    const link = homeworkLink({ url: 'https://example.org/material' }, async () => { reads++; }, assert.fail);
    await link.handlers.click({ type: 'click', ctrlKey: true, preventDefault: assert.fail });
    await link.handlers.auxclick({ type: 'auxclick', button: 1, preventDefault: assert.fail });
    assert.equal(reads, 2);
    assert.deepEqual(page.destinations, []);
});

test('failed read retains unread state and reports the error', async () => {
    const page = setup();
    globalThis.fetch = async () => ({ ok: false, json: async () => ({ detail: 'Ошибка сохранения' }) });
    const errors = [];
    const card = notificationCard(item(), { onError: error => errors.push(error.message) });
    card.handlers.click({ target: { closest: () => null } });
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(errors, ['Ошибка сохранения']);
    assert.equal(card.classes.has('is-unread'), true);
    assert.equal(page.events.length, 0);
});

test('login preserves an internal assignment URL and rejects external redirect tricks', () => {
    setup();
    assert.equal(safeNextUrl('/python/steps/42?task=7#editor'), '/python/steps/42?task=7#editor');
    for (const value of [null, '//evil.example', '/\\evil.example', 'javascript:alert(1)', 'https://evil.example', '/\n/evil.example']) {
        assert.equal(safeNextUrl(value), '/dashboard');
    }
});

test('an expired session returns to the homework destination after login', async () => {
    setup();
    const redirects = [];
    globalThis.window.location.replace = url => redirects.push(url);
    globalThis.localStorage.removeItem = () => {};
    globalThis.fetch = async () => ({ status: 401 });
    const next = '/python/steps/42?task=7#editor';
    await assert.rejects(authFetch('/api/notifications/12/read', { method: 'POST', loginNext: next }), /authentication-required/);
    assert.equal(new URL(redirects[0], window.location.origin).searchParams.get('next'), next);
});

test('a missing session preserves the homework destination without issuing an API request', async () => {
    const page = setup();
    const redirects = [];
    globalThis.localStorage.getItem = () => null;
    globalThis.window.location.replace = url => redirects.push(url);
    const next = '/python/steps/42#editor';
    await assert.rejects(authFetch('/api/homework/12/read-notification', { method: 'POST', loginNext: next }), /authentication-required/);
    assert.equal(new URL(redirects[0], window.location.origin).searchParams.get('next'), next);
    assert.deepEqual(page.requests, []);
});
