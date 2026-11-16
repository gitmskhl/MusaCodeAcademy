import test from 'node:test';
import assert from 'node:assert/strict';

globalThis.document = { querySelector: () => null };
const { bootstrapAdminPage } = await import('../../app/static/js/admin-bootstrap.js');

function setup() {
    const errors = [];
    const loading = { hidden: false, setAttribute(name, value) { this[name] = value; }, replaceChildren(...children) { this.children = children; } };
    globalThis.document = {
        querySelector: () => loading,
        createElement: tag => ({ tag, addEventListener(type, handler) { this[type] = handler; } }),
    };
    let reloads = 0;
    globalThis.window = { location: { reload: () => reloads++ } };
    const script = { src: 'https://mca.example/static/v-release/js/admin-bootstrap.js', dataset: { adminEntry: 'admin-monitoring.js' } };
    return { loading, script, errors, reloads: () => reloads };
}

test('admin entry loads from the same asset version as the bootstrap', async () => {
    const page = setup();
    const requests = [];
    await bootstrapAdminPage(page.script, { loadModule: async url => { requests.push(url); page.loading.hidden = true; } });
    assert.deepEqual(requests, ['https://mca.example/static/v-release/js/admin-monitoring.js']);
    assert.equal(page.loading.children, undefined);
});

test('a broken module import shows an error and a working retry instead of a stuck access check', async t => {
    const page = setup();
    t.mock.method(console, 'error', () => {});
    await bootstrapAdminPage(page.script, { loadModule: async () => { throw new SyntaxError('Missing export createDeleteHomeworkButton'); } });
    assert.equal(page.loading.role, 'alert');
    assert.match(page.loading.children[0].textContent, /Не удалось загрузить/);
    assert.equal(page.loading.children[1].textContent, 'Повторить загрузку');
    page.loading.children[1].click();
    assert.equal(page.reloads(), 1);
});

test('a stalled access check becomes retryable even when module loading succeeded', async t => {
    const page = setup();
    t.mock.method(console, 'error', () => {});
    await bootstrapAdminPage(page.script, { loadModule: async () => {}, timeoutMs: 5 });
    await new Promise(resolve => setTimeout(resolve, 15));
    assert.equal(page.loading.role, 'alert');
    assert.equal(page.loading.children[1].textContent, 'Повторить загрузку');
});

test('the timeout does not overwrite a page that finished initialising', async () => {
    const page = setup();
    await bootstrapAdminPage(page.script, { loadModule: async () => {}, timeoutMs: 5 });
    page.loading.hidden = true;
    await new Promise(resolve => setTimeout(resolve, 15));
    assert.equal(page.loading.children, undefined);
});
