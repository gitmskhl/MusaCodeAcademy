import test from 'node:test';
import assert from 'node:assert/strict';
import { initAdminNavigation } from '../../app/static/js/admin-navigation.js';

const flush = () => new Promise(resolve => setImmediate(resolve));
function setup(role, ok = true) {
    const link = { hidden: true };
    const handlers = {};
    const state = { token: 'token', role, ok };
    globalThis.document = { querySelectorAll: () => [link] };
    globalThis.window = { addEventListener: (type, handler) => { handlers[type] = handler; } };
    globalThis.localStorage = { getItem: () => state.token };
    globalThis.fetch = async () => ({ ok: state.ok, json: async () => ({ role: state.role }) });
    initAdminNavigation();
    return { link, handlers, state };
}

test('header entry is shown only after the server confirms an administrator', async () => {
    for (const [role, ok, hidden] of [['admin', true, false], ['student', true, true], ['admin', false, true]]) {
        const view = setup(role, ok);
        assert.equal(view.link.hidden, true);
        await flush();
        assert.equal(view.link.hidden, hidden);
    }
});

test('switching accounts or clearing the session immediately hides the admin entry', async () => {
    const view = setup('admin');
    await flush();
    view.state.role = 'student';
    view.handlers.storage({ key: 'musa_code_academy_token' });
    assert.equal(view.link.hidden, true);
    await flush();
    assert.equal(view.link.hidden, true);
    view.state.role = 'admin';
    view.handlers.pageshow({ persisted: true });
    await flush();
    assert.equal(view.link.hidden, false);
    view.state.token = null;
    view.handlers.storage({ key: null });
    assert.equal(view.link.hidden, true);
});
