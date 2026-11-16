import { el, notificationCard } from './notifications.js';

const bell = document.querySelector('[data-notification-bell]');
if (bell) {
    const toggle = bell.querySelector('[data-notification-toggle]');
    const dropdown = bell.querySelector('.notification-dropdown');
    const counter = bell.querySelector('[data-notification-count]');
    const latest = bell.querySelector('[data-notification-latest]');
    const feedback = bell.querySelector('[data-notification-feedback]');
    let version = 0;
    const close = () => { dropdown.hidden = true; toggle.setAttribute('aria-expanded', 'false'); };
    const showError = error => { feedback.textContent = error.message; };
    async function load() {
        const token = localStorage.getItem('musa_code_academy_token');
        if (!token) { bell.hidden = true; return; }
        const request = ++version;
        try {
            const response = await fetch('/api/notifications?page_size=10', { headers: { Authorization: `Bearer ${token}` } });
            if (request !== version) return;
            if (response.status === 401 || response.status === 403) { bell.hidden = true; return; }
            if (!response.ok) throw new Error('Не удалось загрузить уведомления. Обновите страницу.');
            const data = await response.json();
            if (request !== version) return;
            bell.hidden = false;
            counter.textContent = data.unread_count > 99 ? '99+' : String(data.unread_count);
            counter.hidden = !data.unread_count;
            toggle.setAttribute('aria-label', `Уведомления, непрочитанных: ${data.unread_count}`);
            feedback.textContent = '';
            latest.replaceChildren(...data.items.map(item => notificationCard(item, { compact: true, onError: showError })));
            if (!data.items.length) latest.append(el('p', 'Пока нет уведомлений.', 'notification-meta'));
        } catch (error) { bell.hidden = false; showError(error); }
    }
    toggle.addEventListener('click', () => {
        dropdown.hidden = !dropdown.hidden;
        toggle.setAttribute('aria-expanded', String(!dropdown.hidden));
    });
    bell.addEventListener('keydown', event => {
        if (event.key === 'Escape') { close(); toggle.focus(); }
    });
    bell.addEventListener('focusout', event => { if (!bell.contains(event.relatedTarget)) close(); });
    document.addEventListener('click', event => { if (!bell.contains(event.target)) close(); });
    document.addEventListener('notifications-changed', load);
    void load();
}
