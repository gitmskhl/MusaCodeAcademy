import { requireCurrentUser } from './course-auth.js';
import { api, changed, el, homeworkDetails, homeworkLink, notificationCard, pager } from './notifications.js';

const view = document.body.dataset.inbox;
const list = document.querySelector('[data-inbox-list]');
const status = document.querySelector('[data-inbox-status]');
const pagination = document.querySelector('[data-inbox-pagination]');
const readAll = document.querySelector('[data-read-all]');
let loading = false;
let version = 0;

const showError = error => { status.textContent = error.message; status.setAttribute('role', 'alert'); };
async function load() {
    const request = ++version;
    status.textContent = 'Загрузка…';
    status.setAttribute('role', 'status');
    list.setAttribute('aria-busy', 'true');
    const params = new URLSearchParams(location.search);
    const page = Math.max(1, Number(params.get('page')) || 1);
    try {
        const data = await api(`/api/${view}?page=${page}`);
        if (request !== version) return;
        list.replaceChildren(...data.items.map(item => {
            if (view === 'notifications') return notificationCard(item, { onError: showError });
            const card = el('article', null, 'notification-card');
            card.append(el('h2', item.title), homeworkDetails(item), homeworkLink(item, async loginNext => {
                await api(`/api/homework/${item.id}/read-notification`, { method: 'POST', keepalive: true, loginNext });
                changed();
            }, showError));
            return card;
        }));
        status.textContent = data.items.length ? '' : view === 'notifications' ? 'Пока нет уведомлений.' : 'Домашние задания пока не назначены.';
        pagination.replaceChildren(pager(data, next => {
            history.pushState(null, '', `${location.pathname}?page=${next}`);
            void load();
        }));
        if (readAll) readAll.disabled = !data.unread_count;
    } catch (error) { if (request === version) showError(error); }
    finally { if (request === version) list.setAttribute('aria-busy', 'false'); }
}

readAll?.addEventListener('click', async () => {
    if (loading) return;
    loading = true;
    readAll.disabled = true;
    try { await api('/api/notifications/read-all', { method: 'POST' }); changed(); await load(); }
    catch (error) { showError(error); readAll.disabled = false; }
    finally { loading = false; }
});
window.addEventListener('popstate', load);
document.addEventListener('notifications-changed', () => {
    if (readAll && !loading && !list.querySelector('.is-unread')) readAll.disabled = true;
});
async function init() {
    try {
        const user = await requireCurrentUser();
        document.querySelector('[data-app-profile-button]').textContent = user.first_name.charAt(0).toUpperCase();
        document.querySelector('[data-inbox-shell]').hidden = false;
        await load();
    } catch (error) { if (error.message !== 'authentication-required') showError(error); }
}
void init();
