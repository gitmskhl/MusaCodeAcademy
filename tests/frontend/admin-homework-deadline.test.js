import test from 'node:test';
import assert from 'node:assert/strict';
import { createUserIdWithHomework, refreshHomeworkDeadlines } from '../../app/static/js/admin-homework-deadline.js';

class Element {
    constructor() { this.children = []; this.dataset = {}; this.attributes = {}; }
    append(...nodes) { this.children.push(...nodes); }
    setAttribute(key, value) { this.attributes[key] = value; }
}

function indicator(homework, now = new Date(2026, 10, 24, 23, 59, 59)) {
    globalThis.document = {
        createElement: () => new Element(),
        createTextNode: text => ({ textContent: text }),
    };
    const cell = createUserIdWithHomework({ id: 7, latest_homework: homework }, now);
    assert.equal(cell.children[1].textContent, '7');
    const dot = cell.children[0];
    assert.equal(dot.attributes.role, 'img');
    assert.equal(dot.attributes['aria-label'], dot.title);
    return dot;
}

test('a future deadline and today stay green, a past deadline is red', () => {
    for (const [due_date, state] of [['2026-11-25', 'upcoming'], ['2026-11-24', 'upcoming'], ['2026-11-23', 'overdue']]) {
        const dot = indicator({ id: 1, due_date });
        assert.equal(dot.className, `homework-deadline homework-deadline--${state}`);
        assert.match(dot.title, new RegExp(due_date.split('-').reverse().join('\\.')));
    }
});

test('missing homework and latest homework without a deadline are gray with distinct labels', () => {
    const missing = indicator(null);
    const undated = indicator({ id: 1, due_date: null });
    assert.equal(missing.className, 'homework-deadline homework-deadline--none');
    assert.equal(undated.className, missing.className);
    assert.equal(missing.title, 'ДЗ не назначалось');
    assert.equal(undated.title, 'Последнее ДЗ без срока сдачи');
});

test('deadline uses the browser day when UTC is still the previous day', () => {
    const previous = process.env.TZ;
    process.env.TZ = 'Europe/Istanbul';
    try {
        const dot = indicator({ id: 1, due_date: '2026-11-23' }, new Date('2026-11-23T22:00:00Z'));
        assert.match(dot.className, /--overdue$/);
    } finally {
        if (previous === undefined) delete process.env.TZ;
        else process.env.TZ = previous;
    }
});

test('an open page switches to red at the start of the next day', () => {
    const dot = indicator({ id: 1, due_date: '2026-12-31' }, new Date(2026, 11, 31, 23, 59));
    assert.match(dot.className, /--upcoming$/);
    refreshHomeworkDeadlines({ querySelectorAll: () => [dot] }, new Date(2027, 0, 1));
    assert.match(dot.className, /--overdue$/);
    assert.match(dot.attributes['aria-label'], /срок прошёл/);
});
