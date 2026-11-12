import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../../app/static/js/course-icon-upload.js', import.meta.url), 'utf8')
    .replace('export function', 'function');

function setup(initialUrl = null, response = () => ({
    ok: true, json: async () => ({ storage_path: 'images/uploaded.png' }),
})) {
    const requests = [];
    const revoked = [];
    const element = () => ({
        hidden: false, disabled: false, textContent: '', handlers: {}, attributes: {},
        addEventListener(event, handler) { this.handlers[event] = handler; },
        setAttribute(name, value) { this.attributes[name] = value; },
        removeAttribute(name) { delete this.attributes[name]; },
        focus() { this.focused = true; },
    });
    const input = Object.assign(element(), { files: [] });
    Object.defineProperty(input, 'value', { set(value) { if (value === '') this.files = []; } });
    const preview = element();
    const image = element();
    const remove = element();
    const error = element();
    const nodes = {
        '#course-icon': input, '[data-course-icon-preview]': preview,
        '[data-course-icon-image]': image, '[data-course-icon-remove]': remove,
        '[data-error-for="icon"]': error,
    };
    const controller = vm.runInNewContext(`${source}\ninitCourseIconUpload(form, initialUrl)`, {
        form: { querySelector: (selector) => nodes[selector] }, initialUrl,
        URL: { createObjectURL: () => 'blob:preview', revokeObjectURL: (url) => revoked.push(url) },
        window: { addEventListener() {} },
        FormData: class { append(name, file) { this[name] = file; } },
        fetch: async (...args) => { requests.push(args); return response(); },
        Error, TypeError,
    });
    return {
        controller, input, preview, image, error, remove, requests, revoked,
        select(file) { input.files = [file]; input.handlers.change(); },
    };
}

const png = { name: 'icon.png', type: 'image/png', size: 100 };

test('keeps the current icon unless the admin removes or replaces it', async () => {
    const page = setup('/uploads/images/existing.png');
    assert.equal(page.image.src, '/uploads/images/existing.png');
    assert.equal(page.preview.hidden, false);
    assert.equal(await page.controller.upload('token'), '/uploads/images/existing.png');
    assert.equal(page.requests.length, 0);
    page.remove.handlers.click();
    assert.equal(page.preview.hidden, true);
    assert.equal(await page.controller.upload('token'), null);
});

test('previews locally, sends authenticated multipart, and reuses the upload on save retry', async () => {
    const page = setup();
    page.select(png);
    assert.equal(page.image.src, 'blob:preview');
    assert.equal(page.requests.length, 0);
    page.controller.setBusy(true);
    assert.equal(page.input.disabled, true);
    assert.equal(page.remove.disabled, true);
    assert.equal(await page.controller.upload('token'), '/uploads/images/uploaded.png');
    const [url, request] = page.requests[0];
    assert.equal(url, '/api/files/images');
    assert.equal(request.headers.Authorization, 'Bearer token');
    assert.equal(request.headers['Content-Type'], undefined);
    assert.equal(request.body.file, png);
    assert.deepEqual(page.revoked, ['blob:preview']);
    assert.equal(await page.controller.upload('token'), '/uploads/images/uploaded.png');
    assert.equal(page.requests.length, 1);
    page.controller.setBusy(false);
    assert.equal(page.input.disabled, false);
});

test('removing a selected file clears its preview and avoids uploading it', async () => {
    const page = setup('/uploads/images/existing.png');
    page.select(png);
    page.remove.handlers.click();
    assert.equal(page.preview.hidden, true);
    assert.deepEqual(page.revoked, ['blob:preview']);
    assert.equal(await page.controller.upload('token'), null);
    assert.equal(page.requests.length, 0);
});

test('rejects unsupported, empty, and oversized files before upload', async () => {
    for (const file of [
        { name: 'icon.svg', type: 'image/svg+xml', size: 100 },
        { ...png, size: 0 }, { ...png, size: 10 * 1024 * 1024 + 1 },
    ]) {
        const page = setup();
        page.select(file);
        await assert.rejects(page.controller.upload('token'));
        assert.equal(page.requests.length, 0);
        assert.equal(page.input.attributes['aria-invalid'], 'true');
        assert.equal(page.input.focused, true);
        assert.ok(page.error.textContent);
    }
});

test('keeps the selected file after a failed upload so the admin can retry', async () => {
    let failed = true;
    const page = setup(null, () => failed
        ? { ok: false, status: 500 }
        : { ok: true, json: async () => ({ storage_path: 'images/retried.png' }) });
    page.select(png);
    await assert.rejects(page.controller.upload('token'), /Не удалось загрузить иконку/);
    assert.equal(page.input.files[0], png);
    failed = false;
    assert.equal(await page.controller.upload('token'), '/uploads/images/retried.png');
    assert.equal(page.error.textContent, '');
});
