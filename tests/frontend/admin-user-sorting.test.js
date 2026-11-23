import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../../app/static/js/admin-monitoring.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '')
    .replace('void init();', '');

class Element {
    constructor(tag) {
        this.tag = tag;
        this.children = [];
        this.handlers = {};
        this.attributes = {};
        this.style = {};
        this.value = '';
    }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    setAttribute(name, value) { this.attributes[name] = value; }
    addEventListener(name, handler) { this.handlers[name] = handler; }
    get elements() {
        return this.children.flatMap(child => ['input', 'select', 'button'].includes(child.tag) ? [child] : child.elements);
    }
}

function setup(search = '') {
    const nodes = new Map();
    const document = {
        body: { dataset: { view: 'users' } },
        createElement: tag => new Element(tag),
        createTextNode: text => ({ textContent: text }),
        addEventListener() {},
        querySelector(selector) {
            if (!nodes.has(selector)) nodes.set(selector, new Element('div'));
            return nodes.get(selector);
        },
    };
    const location = { pathname: '/admin/users', search };
    const content = document.querySelector('[data-content]');
    const context = vm.createContext({
        document, location, Node: Element, URLSearchParams,
        window: { addEventListener() {}, setInterval() {} },
        history: { pushState(state, unused, url) { location.search = new URL(url, 'https://example.com').search; } },
        FormData: class { constructor(form) { return form.elements.filter(input => input.name).map(input => [input.name, input.value]); } },
        createUserIdWithHomework: user => new Element('a'),
    });
    vm.runInContext(`${source}\nload = async () => {}; api = async () => [];`, context);
    const render = () => {
        content.replaceChildren();
        vm.runInContext(`renderUsers({ items: [{ id: 1, first_name: 'Иван', last_name: 'Петров', email: 'student@example.com', solved_tasks_count: 0, submissions_count: 0 }], total: 75, page: 2, page_size: 25 });`, context);
    };
    const headers = () => content.children[0].children[0].children[0].children[0].children[0].children;
    render();
    return { context, document, location, content, render, headers, params: () => new URLSearchParams(location.search) };
}

test('only the three user columns are sortable and registration initially shows descending order', () => {
    const page = setup();
    assert.deepEqual(page.headers().filter(cell => cell.children.length).map(cell => cell.children[0].textContent),
        ['ID', 'Регистрация', 'Учебная активность']);
    assert.equal(page.headers()[4].attributes['aria-sort'], 'descending');
    assert.equal(page.headers()[4].children[0].children[0].textContent, '↓');
});

test('each column toggles direction, preserves filters and page size, and returns to page one', () => {
    for (const [column, key] of [[0, 'id'], [4, 'created_at'], [5, 'last_activity_at']]) {
        const page = setup('?q=Иван&role=student&blocked=false&course_id=7&page_size=50&page=3');
        const initialOrder = key === 'created_at' ? 'asc' : 'desc';
        for (const order of [initialOrder, initialOrder === 'asc' ? 'desc' : 'asc']) {
            page.headers()[column].children[0].handlers.click();
            assert.equal(page.params().get('sort_by'), key);
            assert.equal(page.params().get('sort_order'), order);
            assert.equal(page.params().has('page'), false);
            for (const [name, value] of Object.entries({ q: 'Иван', role: 'student', blocked: 'false', course_id: '7', page_size: '50' })) {
                assert.equal(page.params().get(name), value);
            }
            page.render();
            assert.equal(page.headers()[column].attributes['aria-sort'], order === 'asc' ? 'ascending' : 'descending');
        }
    }
});

test('pagination and applying filters preserve sorting, while reset restores defaults', async () => {
    const page = setup('?sort_by=last_activity_at&sort_order=asc&page=2');
    const pager = page.content.children[0].children[1];
    pager.children[1].children[1].handlers.click();
    assert.equal(page.params().get('page'), '3');
    assert.equal(page.params().get('sort_by'), 'last_activity_at');
    assert.equal(page.params().get('sort_order'), 'asc');
    await vm.runInContext('setupFilters()', page.context);
    const form = page.document.querySelector('[data-filter-form]');
    form.elements.find(input => input.name === 'q').value = 'Петров';
    form.handlers.submit({ preventDefault() {} });
    assert.equal(page.params().get('q'), 'Петров');
    assert.equal(page.params().get('sort_by'), 'last_activity_at');
    assert.equal(page.params().get('sort_order'), 'asc');
    assert.equal(page.params().has('page'), false);
    form.children.at(-1).handlers.click();
    assert.equal(page.location.search, '');
});
