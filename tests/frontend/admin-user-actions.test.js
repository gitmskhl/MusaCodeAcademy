import test from 'node:test';
import assert from 'node:assert/strict';
import { createDeleteUserButton, createDeleteHomeworkButton, createEnrollmentAction, createEnrollmentForm } from '../../app/static/js/admin-user-actions.js';

class Element {
    constructor(tag) {
        this.tag = tag;
        this.children = [];
        this.handlers = {};
        this.value = '';
    }
    append(...children) { children.forEach(child => { child.parent = this; this.children.push(child); }); }
    setAttribute() {}
    addEventListener(name, handler) { this.handlers[name] = handler; }
    showModal() { this.open = true; }
    close() { this.open = false; this.handlers.close?.(); }
    remove() { this.parent.children = this.parent.children.filter(child => child !== this); }
}

const submit = form => form.handlers.submit({ preventDefault() {} });

test('homework deletion asks for confirmation, allows cancel and uses the student-scoped URL', async () => {
    const page = setup();
    const trigger = createDeleteHomeworkButton({ ...page, homework: { id: 42, title: '<script>Практика</script>' }, onDeleted: () => page.notices.push('deleted') });
    const first = page.openDialog(trigger);
    assert.match(first.form.children[1].textContent, /<script>Практика<\/script>/);
    assert.match(first.form.children[1].textContent, /связанное уведомление/);
    first.cancel.handlers.click();
    assert.deepEqual(page.requests, []);
    const second = page.openDialog(trigger);
    await submit(second.form);
    assert.deepEqual(page.requests, [['/api/admin/users/7/homework/42', { method: 'DELETE' }]]);
    assert.deepEqual(page.notices, ['deleted']);
    assert.equal(document.body.children.length, 0);
});

test('failed homework deletion keeps the dialog open and allows retry', async () => {
    const page = setup({ fail: true });
    const trigger = createDeleteHomeworkButton({ ...page, homework: { id: 42, title: 'Практика' }, onDeleted: () => page.notices.push('deleted') });
    const dialog = page.openDialog(trigger);
    await submit(dialog.form);
    assert.equal(dialog.error.textContent, 'Нет доступа');
    assert.equal(dialog.confirm.disabled, false);
    assert.deepEqual(page.notices, []);
    page.state.fail = false;
    await submit(dialog.form);
    assert.deepEqual(page.notices, ['deleted']);
});

function setup({ enrolled = true, fail = false, request } = {}) {
    globalThis.document = { createElement: tag => new Element(tag), body: new Element('body') };
    const user = { id: 7, first_name: '<b>Иван</b>', last_name: 'Петров', email: 'student@example.com', courses: [{ id: 1, enrolled }] };
    const course = { id: 1, title: '<script>Python</script>', enrolled };
    const courses = [course, { id: 2, title: 'Java', is_published: false }];
    const requests = [];
    const notices = [];
    const state = { fail };
    const api = async (...args) => {
        requests.push(args);
        if (state.fail) throw new Error('Нет доступа');
        return request?.();
    };
    const onSaved = message => notices.push(message);
    const openDialog = trigger => {
        trigger.handlers.click();
        const dialog = document.body.children[0];
        const form = dialog.children[0];
        const actions = form.children.at(-1);
        return { dialog, form, error: form.children.at(-2), cancel: actions.children[0], confirm: actions.children[1] };
    };
    return { user, course, courses, requests, notices, api, onSaved, state, openDialog };
}

test('enrollment selector excludes current enrollments and labels drafts', async () => {
    const page = setup();
    const form = createEnrollmentForm(page);
    const select = form.children[0].children[0];
    assert.deepEqual(select.children.map(option => option.textContent), ['Выберите курс', 'Java (черновик)']);
    await submit(form);
    assert.equal(page.requests.length, 0);
    select.value = '2';
    await submit(form);
    assert.deepEqual(page.requests, [['/api/admin/users/7/courses/2', { method: 'PUT' }]]);
    assert.equal(page.notices.length, 1);
});

test('empty enrollment selector cannot submit', async () => {
    const page = setup();
    const form = createEnrollmentForm({ ...page, courses: [page.course] });
    assert.equal(form.children[0].children[0].disabled, true);
    assert.equal(form.children[1].disabled, true);
    await submit(form);
    assert.equal(page.requests.length, 0);
});

test('failed enrollment preserves selection and allows retry', async () => {
    const page = setup({ fail: true });
    const form = createEnrollmentForm(page);
    const select = form.children[0].children[0];
    select.value = '2';
    await submit(form);
    assert.equal(form.children[2].textContent, 'Нет доступа');
    assert.equal(select.value, '2');
    assert.equal(select.disabled, false);
    assert.equal(page.notices.length, 0);
    page.state.fail = false;
    await submit(form);
    assert.equal(page.notices.length, 1);
});

test('unenrollment requires confirmation and cancel leaves enrollment unchanged', async () => {
    const page = setup();
    const trigger = createEnrollmentAction(page);
    const first = page.openDialog(trigger);
    assert.match(first.form.children[1].textContent, /<script>Python<\/script>/);
    assert.match(first.form.children[1].textContent, /прогресс сохранятся/);
    assert.equal(page.requests.length, 0);
    first.cancel.handlers.click();
    assert.equal(document.body.children.length, 0);
    const second = page.openDialog(trigger);
    await submit(second.form);
    assert.deepEqual(page.requests, [['/api/admin/users/7/courses/1', { method: 'DELETE' }]]);
    assert.match(page.notices[0], /прогресс сохранены/);
    assert.equal(document.body.children.length, 0);
});

test('previously unenrolled course can be enrolled again', async () => {
    const page = setup({ enrolled: false });
    const action = createEnrollmentAction(page);
    await action.children[0].handlers.click();
    assert.deepEqual(page.requests, [['/api/admin/users/7/courses/1', { method: 'PUT' }]]);
    assert.equal(page.notices.length, 1);
});

test('deletion requires matching email and reports request failures in the dialog', async () => {
    const page = setup({ fail: true });
    const trigger = createDeleteUserButton({ ...page, adminId: 8, onDeleted: () => page.notices.push('deleted') });
    const { dialog, form, error } = page.openDialog(trigger);
    assert.match(form.children[1].textContent, /<b>Иван<\/b>/);
    const confirmation = form.children[2].children[0];
    confirmation.value = 'wrong@example.com';
    await submit(form);
    assert.match(error.textContent, /Email не совпадает/);
    assert.equal(page.requests.length, 0);
    confirmation.value = page.user.email;
    await submit(form);
    assert.equal(dialog.open, true);
    assert.equal(error.textContent, 'Нет доступа');
    assert.equal(page.notices.length, 0);
    assert.equal(confirmation.disabled, false);
    page.state.fail = false;
    await submit(form);
    assert.deepEqual(page.requests.at(-1), ['/api/admin/users/7', { method: 'DELETE' }]);
    assert.deepEqual(page.notices, ['deleted']);
    assert.equal(document.body.children.length, 0);
});

test('self deletion is disabled', () => {
    const page = setup();
    const trigger = createDeleteUserButton({ ...page, adminId: page.user.id });
    assert.equal(trigger.disabled, true);
    assert.match(trigger.title, /собственный аккаунт/);
});

test('pending deletion prevents duplicate requests and dismissing the dialog', async () => {
    let finish;
    const page = setup({ request: () => new Promise(resolve => { finish = resolve; }) });
    const trigger = createDeleteUserButton({ ...page, adminId: 8, onDeleted: () => {} });
    const { dialog, form, cancel, confirm } = page.openDialog(trigger);
    form.children[2].children[0].value = page.user.email;
    const pending = submit(form);
    await submit(form);
    let prevented = false;
    dialog.handlers.cancel({ preventDefault() { prevented = true; } });
    assert.equal(prevented, true);
    assert.equal(cancel.disabled, true);
    assert.equal(confirm.disabled, true);
    assert.equal(page.requests.length, 1);
    finish();
    await pending;
});
