import { createCodeEditorView } from './step-renderer/codemirror/code-editor-view.js';

const TOKEN_KEY = 'musa_code_academy_token';
const view = document.body.dataset.view;
const recordId = document.body.dataset.recordId;
const content = document.querySelector('[data-content]');
const errorBox = document.querySelector('[data-error]');
const filterForm = document.querySelector('[data-filter-form]');
const dialog = document.querySelector('[data-block-dialog]');
const blockForm = document.querySelector('[data-block-form]');
const statuses = {
    PENDING: 'В очереди', RUNNING: 'Проверяется', ACCEPTED: 'Принято',
    'WRONG ANSWER': 'Неверный ответ', RUNTIME_ERROR: 'Ошибка выполнения',
    COMPILATION_ERROR: 'Ошибка компиляции', TIME_LIMIT_EXCEEDED: 'Превышено время',
    MEMORY_LIMIT_EXCEEDED: 'Превышена память', SYSTEM_ERROR: 'Системная ошибка', FAILED: 'Сбой проверки',
};
let currentAdmin;
let currentUser;
let codeEditor;
let requestVersion = 0;
let savingBlock = false;

// All user-authored content goes through textContent, including code and output.
function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (className) node.className = className;
    return node;
}
function link(text, href, className = '') {
    const node = el('a', text, className);
    node.href = href;
    return node;
}
function button(text, handler, className = 'button button--ghost') {
    const node = el('button', text, className);
    node.type = 'button';
    node.addEventListener('click', handler);
    return node;
}
function date(value) {
    return value ? new Date(value).toLocaleString('ru-RU') : 'Нет данных';
}
function badge(text, good = false, danger = false) {
    const node = el('span', text, `status-badge status-badge--${good ? 'published' : 'draft'}`);
    if (danger) {
        node.style.background = 'var(--danger-bg)';
        node.style.color = 'var(--danger-text)';
    }
    return node;
}
function statusBadge(status) {
    return badge(statuses[status] || status, status === 'ACCEPTED', !['PENDING', 'RUNNING', 'ACCEPTED'].includes(status));
}
function showError(error) {
    errorBox.textContent = error.message || 'Не удалось загрузить данные. Попробуйте ещё раз.';
    errorBox.hidden = false;
}
async function api(path, options = {}) {
    const response = await fetch(path, {
        ...options,
        headers: { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`, ...options.headers },
    });
    if (response.status === 401) {
        localStorage.removeItem(TOKEN_KEY);
        location.assign('/login');
        throw new Error('Войдите в аккаунт заново.');
    }
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(typeof data.detail === 'string' ? data.detail : 'Не удалось выполнить запрос. Проверьте фильтры и попробуйте ещё раз.');
    }
    return response.json();
}
function section(title) {
    const node = el('section', null, 'section-block');
    if (title) node.append(el('h2', title, 'monitoring-section-heading'));
    return node;
}
function table(headers, rows) {
    if (!rows.length) return el('p', 'По этим условиям ничего не найдено.', 'monitoring-empty');
    const wrap = el('div', null, 'monitoring-table-wrap');
    const node = el('table', null, 'monitoring-table');
    const head = el('thead');
    const headRow = el('tr');
    headers.forEach(text => {
        const cell = el('th', text);
        cell.scope = 'col';
        headRow.append(cell);
    });
    head.append(headRow);
    const body = el('tbody');
    rows.forEach(cells => {
        const row = el('tr');
        cells.forEach(value => {
            const cell = el('td');
            cell.append(value instanceof Node ? value : document.createTextNode(String(value)));
            row.append(cell);
        });
        body.append(row);
    });
    node.append(head, body);
    wrap.append(node);
    return wrap;
}
function stacked(primary, secondary) {
    const node = el('div');
    node.append(primary instanceof Node ? primary : el('span', primary));
    if (secondary) node.append(el('span', secondary, 'monitoring-muted'));
    return node;
}
function setQuery(params) {
    const query = params.toString();
    history.pushState(null, '', `${location.pathname}${query ? `?${query}` : ''}`);
    void load();
}
function pager(data, onPage) {
    const node = el('div', null, 'monitoring-pager');
    const pages = Math.max(1, Math.ceil(data.total / data.page_size));
    node.append(el('span', `Всего: ${data.total} · Страница ${data.page} из ${pages}`));
    const actions = el('div');
    const previous = button('← Назад', () => onPage(data.page - 1));
    const next = button('Далее →', () => onPage(data.page + 1));
    previous.disabled = data.page <= 1;
    next.disabled = data.page >= pages;
    actions.append(previous, next);
    node.append(actions);
    return node;
}
function submissionTable(items) {
    return table(['Отправка', 'Пользователь', 'Задача / курс', 'Результат', 'Тесты', 'Дата'], items.map(item => [
        link(`#${item.id}`, `/admin/submissions/${item.id}`),
        stacked(link(item.user_name, `/admin/users/${item.user_id}`), item.user_email),
        stacked(link(item.step_title, `/admin/steps/${item.step_id}/task`), `${item.course_title} · ${item.lesson_title} · Задача #${item.task_id}`),
        statusBadge(item.status),
        `${item.passed_tests} / ${item.total_tests ?? '—'}`,
        date(item.submitted_at),
    ]));
}
function filter(name, label, choices = null, type = 'text') {
    const wrapper = el('div', null, 'field');
    const caption = el('label', label);
    caption.htmlFor = `filter-${name}`;
    wrapper.append(caption);
    const input = el(choices ? 'select' : 'input');
    input.id = `filter-${name}`;
    input.name = name;
    if (choices) choices.forEach(([value, text]) => {
        const option = el('option', text);
        option.value = value;
        input.append(option);
    });
    else {
        input.type = type;
        if (type === 'number') { input.min = '1'; input.step = '1'; }
        if (type === 'text') input.maxLength = 255;
    }
    if (name === 'q') input.placeholder = 'Имя, email или ID';
    if (type === 'date') input.max = '9999-12-30';
    wrapper.append(input);
    filterForm.append(wrapper);
}
async function setupFilters() {
    if (!['users', 'submissions'].includes(view)) return;
    const courses = await api('/api/admin/courses');
    filter('q', 'Поиск пользователя');
    filter('course_id', view === 'users' ? 'Записан на курс' : 'Курс', [['', 'Все курсы'], ...courses.map(course => [course.id, course.title])]);
    if (view === 'users') {
        filter('role', 'Роль', [['', 'Все роли'], ['student', 'Ученик'], ['admin', 'Администратор']]);
        filter('blocked', 'Аккаунт', [['', 'Все'], ['false', 'Активные'], ['true', 'Заблокированные']]);
    } else {
        filter('user_id', 'ID пользователя', null, 'number');
        filter('task_id', 'ID задачи', null, 'number');
        filter('status', 'Результат', [['', 'Все результаты'], ...Object.entries(statuses)]);
        filter('date_from', 'С даты (UTC)', null, 'date');
        filter('date_to', 'По дату (UTC)', null, 'date');
    }
    filter('page_size', 'На странице', [['25', '25'], ['50', '50'], ['100', '100']]);
    const apply = el('button', 'Применить', 'button button--primary');
    apply.type = 'submit';
    filterForm.append(apply, button('Сбросить', () => setQuery(new URLSearchParams())));
    filterForm.addEventListener('submit', event => {
        event.preventDefault();
        const params = new URLSearchParams();
        for (const [key, value] of new FormData(filterForm)) if (value) params.set(key, value);
        setQuery(params);
    });
    document.querySelector('[data-filters]').hidden = false;
}
function syncFilters() {
    const params = new URLSearchParams(location.search);
    for (const input of filterForm.elements) {
        if (input.name) input.value = params.get(input.name) || (input.name === 'page_size' ? '25' : '');
    }
}
function renderUsers(data) {
    const node = section();
    node.append(table(['ID', 'Пользователь', 'Аккаунт', 'Регистрация', 'Учебная активность', 'Решено задач', 'Отправки'], data.items.map(user => [
        user.id,
        stacked(link(`${user.first_name} ${user.last_name}`, `/admin/users/${user.id}`), user.email),
        stacked(badge(user.blocked_at ? 'Заблокирован' : 'Активен', !user.blocked_at, !!user.blocked_at), user.role === 'admin' ? 'Администратор' : 'Ученик'),
        date(user.created_at), date(user.last_activity_at), user.solved_tasks_count,
        link(user.submissions_count, `/admin/submissions?user_id=${user.id}`),
    ])));
    node.append(pager(data, page => {
        const params = new URLSearchParams(location.search);
        params.set('page', page);
        setQuery(params);
    }));
    content.append(node);
}
function renderSubmissions(data) {
    const node = section();
    node.append(submissionTable(data.items), pager(data, page => {
        const params = new URLSearchParams(location.search);
        params.set('page', page);
        setQuery(params);
    }));
    content.append(node);
}
function meta(entries) {
    const node = el('dl', null, 'monitoring-meta');
    entries.forEach(([label, value]) => {
        const item = el('div');
        const description = el('dd');
        description.append(value instanceof Node ? value : document.createTextNode(String(value)));
        item.append(el('dt', label), description);
        node.append(item);
    });
    return node;
}
function openBlockDialog() {
    const blocking = !currentUser.blocked_at;
    blockForm.reset();
    document.querySelector('[data-block-error]').textContent = '';
    document.querySelector('[data-block-title]').textContent = blocking ? 'Блокировка пользователя' : 'Разблокировка пользователя';
    document.querySelector('[data-block-description]').textContent = `${currentUser.first_name} ${currentUser.last_name} (${currentUser.email}). ${blocking ? 'Доступ к аккаунту будет закрыт. Решения и прогресс сохранятся.' : 'Доступ к аккаунту будет восстановлен.'}`;
    document.querySelector('[data-reason-field]').hidden = !blocking;
    blockForm.elements.reason.required = blocking;
    const submit = document.querySelector('[data-block-submit]');
    submit.textContent = blocking ? 'Заблокировать' : 'Разблокировать';
    submit.className = `button button--${blocking ? 'danger' : 'primary'}`;
    dialog.showModal();
}
function renderUser(user, submissions) {
    currentUser = user;
    const profile = section();
    const actions = el('div', null, 'monitoring-section-heading');
    actions.append(badge(user.blocked_at ? 'Заблокирован' : 'Активен', !user.blocked_at, !!user.blocked_at));
    const toggle = button(user.blocked_at ? 'Разблокировать' : 'Заблокировать', openBlockDialog,
        `button button--${user.blocked_at ? 'primary' : 'danger'}`);
    toggle.disabled = user.id === currentAdmin.id;
    if (toggle.disabled) toggle.title = 'Нельзя заблокировать собственный аккаунт';
    actions.append(toggle);
    profile.append(actions, meta([
        ['Email', user.email], ['Роль', user.role === 'admin' ? 'Администратор' : 'Ученик'],
        ['Регистрация', date(user.created_at)], ['Последний вход', date(user.last_login_at)],
        ['Последняя учебная активность', date(user.last_activity_at)], ['ID', user.id],
        ...(user.blocked_at ? [['Дата блокировки', date(user.blocked_at)], ['Причина', user.block_reason || 'Не указана']] : []),
    ]));
    const stats = el('div', null, 'monitoring-stats');
    [[user.courses.filter(course => course.enrolled).length, 'Текущие записи на курсы'],
        [user.solved_tasks_count, 'Решено уникальных задач'], [user.submissions_count, 'Всего отправок']].forEach(([value, label]) => {
        const stat = el('div', null, 'monitoring-stat');
        stat.append(el('strong', value), el('span', label));
        stats.append(stat);
    });
    profile.append(stats);
    const courses = section('Прогресс по курсам');
    courses.append(el('p', 'Пройденные шаги учитывают отметки о завершении. Решённые задачи — уникальные задачи с принятым решением.', 'monitoring-muted'));
    courses.append(table(['Курс', 'Запись', 'Пройдено шагов', 'Решено задач', 'Отправки', 'Учебная активность'], user.courses.map(course => {
        const progress = el('div', `${course.completed_steps} / ${course.total_steps}`);
        const bar = el('progress', null, 'monitoring-progress');
        bar.max = course.total_steps || 1;
        bar.value = course.completed_steps;
        bar.setAttribute('aria-label', `Пройдено шагов: ${course.completed_steps} из ${course.total_steps}`);
        progress.append(bar);
        return [stacked(link(course.title, `/admin/courses/${course.id}`), course.is_published ? 'Опубликован' : 'Черновик'),
            course.enrolled ? 'Записан' : 'Не записан', progress,
            `${course.solved_tasks} / ${course.total_tasks}`,
            link(course.submissions_count, `/admin/submissions?user_id=${user.id}&course_id=${course.id}`), date(course.last_activity_at)];
    })));
    const attempts = section('Последние отправки');
    attempts.append(link('Все отправки пользователя →', `/admin/submissions?user_id=${user.id}`, 'monitoring-link'));
    attempts.append(submissionTable(submissions.items));
    content.append(profile, courses, attempts);
}
function renderSubmission(item) {
    const info = section();
    info.append(meta([
        ['Пользователь', stacked(link(item.user_name, `/admin/users/${item.user_id}`, 'monitoring-link'), item.user_email)],
        ['Результат', statusBadge(item.status)],
        ['Задача', link(`${item.step_title} (#${item.task_id})`, `/admin/steps/${item.step_id}/task`, 'monitoring-link')],
        ['Курс / урок', `${item.course_title} / ${item.lesson_title}`],
        ['Дата', date(item.submitted_at)], ['Пройдено тестов', `${item.passed_tests} / ${item.total_tests ?? '—'}`],
        ['ID первого непройденного теста', item.failed_test_id ?? '—'],
    ]));
    if (['PENDING', 'RUNNING'].includes(item.status)) {
        info.append(button('Обновить результат', () => void load()));
    }
    const code = section('Код решения');
    const editorHost = el('div', null, 'monitoring-code');
    code.append(editorHost);
    const output = section('Вывод / диагностика');
    output.append(el('pre', item.actual_output ?? 'Сохранённой диагностики нет.', 'monitoring-output'));
    content.append(info, code, output);
    codeEditor = createCodeEditorView({ parent: editorHost, document: item.source_code, language: 'python', editable: false });
}
async function load() {
    const version = ++requestVersion;
    errorBox.hidden = true;
    content.setAttribute('aria-busy', 'true');
    syncFilters();
    for (const control of filterForm.elements) control.disabled = true;
    try {
        let data;
        let submissions;
        if (view === 'user') {
            [data, submissions] = await Promise.all([
                api(`/api/admin/users/${recordId}`),
                api(`/api/admin/submissions?user_id=${recordId}&page_size=10`),
            ]);
        } else if (view === 'submission') data = await api(`/api/admin/submissions/${recordId}`);
        else data = await api(`/api/admin/${view}${location.search}`);
        if (version !== requestVersion) return;
        codeEditor?.destroy();
        codeEditor = null;
        content.replaceChildren();
        if (view === 'users') renderUsers(data);
        else if (view === 'submissions') renderSubmissions(data);
        else if (view === 'user') {
            document.querySelector('[data-title]').textContent = `${data.first_name} ${data.last_name}`;
            renderUser(data, submissions);
        } else renderSubmission(data);
    } catch (error) {
        if (version !== requestVersion) return;
        codeEditor?.destroy();
        codeEditor = null;
        content.replaceChildren(button('Повторить загрузку', () => void load()));
        showError(error);
    } finally {
        if (version === requestVersion) {
            content.setAttribute('aria-busy', 'false');
            for (const control of filterForm.elements) control.disabled = false;
        }
    }
}

document.querySelector('[data-block-cancel]').addEventListener('click', () => dialog.close());
dialog.addEventListener('cancel', event => { if (savingBlock) event.preventDefault(); });
blockForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (savingBlock) return;
    savingBlock = true;
    document.querySelector('[data-block-error]').textContent = '';
    const blocking = !currentUser.blocked_at;
    const reason = blockForm.elements.reason.value.trim();
    for (const control of blockForm.elements) control.disabled = true;
    try {
        await api(`/api/admin/users/${currentUser.id}/block`, {
            method: 'PATCH', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ blocked: blocking, reason: blocking ? reason : null }),
        });
        dialog.close();
        const notice = document.querySelector('[data-notice]');
        notice.textContent = blocking ? 'Пользователь заблокирован. Решения и прогресс сохранены.' : 'Доступ пользователя восстановлен.';
        notice.hidden = false;
        await load();
    } catch (error) {
        document.querySelector('[data-block-error]').textContent = error.message;
    } finally {
        savingBlock = false;
        for (const control of blockForm.elements) control.disabled = false;
    }
});
window.addEventListener('popstate', () => void load());

async function init() {
    try {
        if (!localStorage.getItem(TOKEN_KEY)) { location.assign('/login'); return; }
        currentAdmin = await api('/api/users/me');
        if (currentAdmin.role !== 'admin') throw new Error('Эта страница доступна только администратору.');
        document.querySelector('[data-title]').textContent = {
            users: 'Пользователи', user: 'Карточка пользователя',
            submissions: 'Отправки', submission: `Отправка #${recordId}`,
        }[view];
        document.querySelector('[data-loading]').hidden = true;
        document.querySelector('[data-shell]').hidden = false;
        await setupFilters();
        await load();
    } catch (error) {
        document.querySelector('[data-loading]').hidden = true;
        document.querySelector('[data-shell]').hidden = false;
        showError(error);
    }
}
void init();
