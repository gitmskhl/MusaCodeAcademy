import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../../app/static/js/admin-database-export.js', import.meta.url), 'utf8')
    .replace('export function', 'function');

function setup(fetchResponse) {
    let click;
    const button = { disabled: false, textContent: '', addEventListener: (_, handler) => { click = handler; } };
    const status = { textContent: '' };
    const downloads = [];
    const requests = [];
    const timers = [];
    const revoked = [];
    const document = {
        querySelector: (selector) => selector === '[data-database-export]' ? button : status,
        body: { append() {} },
        createElement: () => ({ click() { downloads.push({ filename: this.download, url: this.href }); }, remove() {} }),
    };
    vm.runInNewContext(`${source}\ninitDatabaseExport();`, {
        document,
        localStorage: { getItem: () => 'admin-token' },
        fetch: async (...args) => { requests.push(args); return fetchResponse(); },
        URL: { createObjectURL: () => 'blob:dump', revokeObjectURL: (url) => revoked.push(url) },
        window: { setTimeout: (fn) => timers.push(fn) },
        Error,
    });
    return { button, status, downloads, requests, timers, revoked, click: () => click() };
}

test('downloads the authenticated export using the server filename', async () => {
    const page = setup(async () => ({
        ok: true, blob: async () => ({}),
        headers: { get: () => 'attachment; filename="musacodeacademy_2026-11-10.dump"' },
    }));
    await page.click();
    assert.equal(page.requests[0][0], '/api/admin/database/export');
    assert.equal(page.requests[0][1].method, 'POST');
    assert.equal(page.requests[0][1].headers.Authorization, 'Bearer admin-token');
    assert.equal(page.downloads[0].filename, 'musacodeacademy_2026-11-10.dump');
    assert.equal(page.button.disabled, false);
    page.timers[0]();
    assert.deepEqual(page.revoked, ['blob:dump']);
});

test('blocks repeated clicks during export and enables the button after an error', async () => {
    let resolve;
    const page = setup(() => new Promise((done) => { resolve = done; }));
    const first = page.click();
    assert.equal(page.button.disabled, true);
    await page.click();
    assert.equal(page.requests.length, 1);
    resolve({ ok: false, json: async () => ({ detail: 'Экспорт уже выполняется.' }) });
    await first;
    assert.equal(page.status.textContent, 'Экспорт уже выполняется.');
    assert.equal(page.downloads.length, 0);
    assert.equal(page.button.disabled, false);
});

test('handles proxy errors without a JSON response', async () => {
    const page = setup(async () => ({ ok: false, json: async () => { throw new Error('HTML response'); } }));
    await page.click();
    assert.match(page.status.textContent, /Не удалось экспортировать/);
    assert.equal(page.button.disabled, false);
    assert.equal(page.downloads.length, 0);
});
