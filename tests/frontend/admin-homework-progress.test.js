import test from 'node:test';
import assert from 'node:assert/strict';
import { createLatestHomeworkSection } from '../../app/static/js/admin-homework-progress.js';

class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.handlers = {}; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    setAttribute(name, value) { this[name] = value; }
    addEventListener(type, handler) { this.handlers[type] = handler; }
}
const flush = () => new Promise(resolve => setImmediate(resolve));
const descendants = node => [node, ...node.children.flatMap(descendants)];
const report = () => ({
    homework: { title: '<b>ДЗ</b>', url: '/python/steps/12', comment: '<script>Комментарий</script>', created_at: '2026-11-22T10:00:00Z' },
    unavailable_reason: null, course_title: 'Python', lesson_title: 'Циклы', total_tasks: 3, solved_tasks: 1,
    steps: [
        { id: 12, title: '<b>Шаг 2</b>', position: 2, task_id: 22, status: 'solved', submissions_count: 2, url: '/python/steps/12?preview=1' },
        { id: 13, title: 'Шаг 3', position: 3, task_id: 23, status: 'attempted', submissions_count: 1, url: '/python/steps/13?preview=1' },
        { id: 14, title: 'Шаг 4', position: 4, task_id: null, status: 'completed', submissions_count: 0, url: '/python/steps/14?preview=1' },
        { id: 15, title: 'Шаг 5', position: 5, task_id: 24, status: 'not_started', submissions_count: 0, url: '/python/steps/15?preview=1' },
    ],
    submissions: { items: [{ id: 99 }], total: 30, page: 1, page_size: 25 },
});
function setup(api = async () => report()) {
    globalThis.document = { createElement: tag => new Element(tag) };
    const requests = [], tables = [];
    let onPage;
    const view = createLatestHomeworkSection({
        user: { id: 7 }, api: (...args) => { requests.push(args); return api(...args); },
        submissionTable: items => { tables.push(items); return new Element('table'); },
        pager: (data, handler) => { onPage = handler; return new Element('nav'); },
    });
    return { ...view, requests, tables, page: number => onPage(number), nodes: () => descendants(view.element) };
}

test('latest homework shows unsolved tasks, theory, literal titles, and the complete submission history', async () => {
    const view = setup();
    await flush();
    const nodes = view.nodes();
    assert.ok(nodes.some(node => node.textContent === '<b>ДЗ</b>'));
    assert.ok(nodes.some(node => node.textContent === '2. <b>Шаг 2</b>'));
    assert.ok(nodes.some(node => node.textContent === 'Теория · Пройдена'));
    assert.ok(nodes.some(node => node.textContent === 'Есть попытки, не решено'));
    assert.ok(nodes.some(node => node.textContent === 'Нет отправок'));
    assert.equal(nodes.filter(node => node.tag === 'li').length, 4);
    assert.ok(nodes.some(node => node.href === '/python/steps/12?preview=1'));
    assert.ok(nodes.some(node => node.href === '/admin/submissions?user_id=7&task_id=22'));
    assert.deepEqual(view.tables, [[{ id: 99 }]]);
    await view.page(2);
    assert.equal(view.requests.at(-1)[0], '/api/admin/users/7/homework/latest-progress?page=2&page_size=25');
});

test('empty and unsupported assignments do not show misleading zero progress', async () => {
    for (const data of [{ homework: null, submissions: { total: 0, page_size: 25 } },
        { ...report(), unavailable_reason: 'Внешняя ссылка' }]) {
        const view = setup(async () => data);
        await flush();
        assert.equal(view.tables.length, 0);
        assert.ok(!view.nodes().some(node => node.tag === 'progress'));
        assert.match(view.element.children[1].textContent, /не назначены|Внешняя ссылка/);
    }
});

test('refresh ignores stale responses and permits retry after a failed request', async () => {
    let finish;
    let requests = 0;
    const view = setup(async () => {
        requests++;
        if (requests === 1) return new Promise(resolve => { finish = resolve; });
        if (requests === 2) throw new Error('Нет соединения');
        return report();
    });
    await view.reload();
    assert.equal(view.element.children[1].textContent, 'Нет соединения');
    assert.equal(view.element.children[0].children[1].disabled, false);
    await view.reload();
    finish({ homework: null, submissions: { total: 0, page_size: 25 } });
    await flush();
    assert.equal(view.element.children[1].textContent, 'Python · Циклы');
    assert.equal(view.tables.length, 1);
});

test('removing a latest assignment resets an out-of-range history page', async () => {
    const view = setup(async url => ({ ...report(), submissions: {
        items: [{ id: 99 }], total: 1, page: Number(new URL(url, 'http://test').searchParams.get('page')), page_size: 25,
    } }));
    await flush();
    await view.page(2);
    assert.equal(view.requests.at(-1)[0], '/api/admin/users/7/homework/latest-progress?page=1&page_size=25');
    assert.equal(view.element['aria-busy'], 'false');
    assert.equal(view.element.children[0].children[1].disabled, false);
});
