import { authFetch } from './course-auth.js';

export function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (className) node.className = className;
    return node;
}

export function errorText(detail) {
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
        const messages = detail.filter(error => error.type === 'value_error')
            .map(error => error.msg.replace(/^Value error, /, ''));
        if (messages.length) return messages.join(' ');
    }
    return 'Не удалось выполнить запрос. Проверьте данные и попробуйте снова.';
}

export async function api(path, options = {}) {
    const response = await authFetch(path, options);
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(errorText(data.detail));
    }
    return response.status === 204 ? null : response.json();
}

export const jsonPost = data => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
export const changed = () => document.dispatchEvent(new Event('notifications-changed'));
export const dateTime = value => new Date(value).toLocaleString('ru-RU');
export const dueDate = value => new Date(`${value}T00:00:00`).toLocaleDateString('ru-RU');

// A real href keeps copy-link, keyboard navigation and opening in a new tab.
// keepalive records reads even when the browser immediately leaves the page.
export function homeworkLink(homework, onRead, onError) {
    const link = el('a', 'Открыть домашнее задание', 'homework-open');
    link.href = homework.url;
    const destination = new URL(homework.url, window.location.origin);
    const loginNext = destination.origin === window.location.origin
        ? `${destination.pathname}${destination.search}${destination.hash}` : undefined;
    const open = async event => {
        if (event.type === 'auxclick' && event.button !== 1) return;
        const nativeNavigation = event.type === 'auxclick' || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey;
        if (!nativeNavigation) event.preventDefault();
        try {
            await onRead(loginNext);
            if (!nativeNavigation) window.location.assign(link.href);
        } catch (error) { onError(error); }
    };
    link.addEventListener('click', open);
    link.addEventListener('auxclick', open);
    return link;
}

export function homeworkDetails(homework, { assigned = true } = {}) {
    const node = el('div', null, 'homework-details');
    if (homework.comment) node.append(el('p', homework.comment, 'notification-text'));
    if (assigned) node.append(el('p', `Назначено: ${dateTime(homework.created_at)}`, 'notification-meta'));
    if (homework.due_date) node.append(el('p', `Срок сдачи: ${dueDate(homework.due_date)}`, 'notification-meta'));
    return node;
}

export function notificationCard(item, { compact = false, onError = () => {} } = {}) {
    const card = el('article', null, `notification-card${compact ? ' notification-card--compact' : ''}`);
    const heading = el('h3');
    const title = el('button', item.title, 'notification-title');
    title.type = 'button';
    const state = el('span', '', 'notification-state');
    const updateState = () => {
        card.classList.toggle('is-unread', !item.read_at);
        state.textContent = item.read_at ? 'Прочитано' : 'Не прочитано';
    };
    updateState();
    let reading;
    const read = async loginNext => {
        if (item.read_at) return;
        if (!reading) reading = api(`/api/notifications/${item.id}/read`, { method: 'POST', keepalive: true, loginNext })
            .then(data => { item.read_at = data.read_at; updateState(); changed(); })
            .finally(() => { reading = null; });
        return reading;
    };
    heading.append(title);
    card.append(heading, state, el('p', dateTime(item.created_at), 'notification-meta'));
    if (item.homework) card.append(homeworkDetails(item.homework, { assigned: false }), homeworkLink(item.homework, read, onError));
    else card.append(el('p', item.text, 'notification-text'));
    card.addEventListener('click', event => {
        if (event.target.closest('a')) return;
        void read().catch(onError);
    });
    return card;
}

export function pager(data, onPage) {
    const node = el('nav', null, 'notification-pager');
    node.setAttribute('aria-label', 'Страницы');
    const pages = Math.max(1, Math.ceil(data.total / data.page_size));
    const previous = el('button', '← Назад', 'student-secondary-link');
    const next = el('button', 'Далее →', 'student-secondary-link');
    previous.type = next.type = 'button';
    previous.disabled = data.page <= 1;
    next.disabled = data.page >= pages;
    previous.addEventListener('click', () => onPage(data.page - 1));
    next.addEventListener('click', () => onPage(data.page + 1));
    node.append(previous, el('span', `Страница ${data.page} из ${pages} · Всего: ${data.total}`), next);
    return node;
}
