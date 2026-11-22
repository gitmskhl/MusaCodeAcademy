import { el, homeworkDetails, jsonPost, pager } from './notifications.js';
import { createDeleteHomeworkButton } from './admin-user-actions.js';

export function createHomeworkSection({ user, api, onChanged = () => {} }) {
    const section = el('section', null, 'section-block');
    section.append(el('h2', 'Домашние задания', 'monitoring-section-heading'));
    const assign = el('button', 'Назначить домашнее задание', 'button button--primary');
    assign.type = 'button';
    assign.setAttribute('aria-expanded', 'false');
    const form = el('form', null, 'admin-form notification-form');
    form.hidden = true;
    function field(name, caption, type = 'text', required = false, value = '') {
        const label = el('label', caption, 'field');
        const input = el(type === 'textarea' ? 'textarea' : 'input');
        input.name = name;
        if (type !== 'textarea') input.type = type;
        else input.rows = 4;
        input.required = required;
        input.defaultValue = value;
        input.value = value;
        if (type !== 'date') input.maxLength = name === 'title' ? 255 : name === 'url' ? 2048 : 10000;
        label.append(input); form.append(label);
    }
    field('title', 'Заголовок', 'text', true, 'Новое домашнее задание');
    field('comment', 'Комментарий (необязательно)', 'textarea');
    field('url', 'Ссылка на задание', 'text', true);
    form.elements.url.placeholder = '/python/steps/12 или https://…';
    field('due_date', 'Срок сдачи (необязательно)', 'date');
    const errorBox = el('p', '', 'field-error');
    errorBox.setAttribute('role', 'alert');
    const save = el('button', 'Назначить и уведомить ученика', 'button button--primary');
    save.type = 'submit';
    const cancel = el('button', 'Отмена', 'button button--ghost');
    cancel.type = 'button';
    const actions = el('div', null, 'form-actions');
    actions.append(save, cancel); form.append(errorBox, actions);
    const status = el('p', '', 'notification-feedback');
    status.setAttribute('role', 'status');
    const list = el('div', null, 'inbox-list');
    const pages = el('div');
    section.append(assign, form, status, list, pages);
    const close = () => { form.hidden = true; assign.hidden = false; assign.setAttribute('aria-expanded', 'false'); };
    assign.addEventListener('click', () => {
        form.hidden = false; assign.hidden = true; assign.setAttribute('aria-expanded', 'true'); form.elements.title.focus();
    });
    cancel.addEventListener('click', close);
    let request = 0;
    let currentPage = 1;
    async function load(page = 1) {
        const version = ++request;
        status.textContent = 'Загружаем домашние задания…';
        try {
            const data = await api(`/api/admin/users/${user.id}/homework?page=${page}&page_size=10`);
            if (version !== request) return;
            const lastPage = Math.max(1, Math.ceil(data.total / data.page_size));
            if (data.page > lastPage) return load(lastPage);
            currentPage = data.page;
            list.replaceChildren(...data.items.map(item => {
                const card = el('article', null, 'notification-card');
                const link = el('a', 'Открыть домашнее задание', 'homework-open');
                link.href = item.url;
                const actions = el('div', null, 'monitoring-actions');
                actions.append(link, createDeleteHomeworkButton({ user, homework: item, api, onDeleted: async () => {
                    await load(currentPage);
                    await onChanged();
                    status.textContent = `Домашнее задание и уведомление удалены. ${status.textContent}`;
                } }));
                card.append(el('h3', item.title), homeworkDetails(item), actions);
                return card;
            }));
            status.textContent = data.total ? `Всего назначено: ${data.total}` : 'Домашние задания пока не назначены.';
            pages.replaceChildren(pager(data, load));
        } catch (error) { if (version === request) status.textContent = error.message; }
    }
    let saving = false;
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (saving) return;
        const payload = {
            title: form.elements.title.value.trim(), comment: form.elements.comment.value.trim() || null,
            url: form.elements.url.value.trim(), due_date: form.elements.due_date.value || null,
        };
        if (!payload.title || !payload.url) { errorBox.textContent = 'Заполните заголовок и ссылку.'; return; }
        saving = true; save.disabled = cancel.disabled = true; errorBox.textContent = '';
        try {
            await api(`/api/admin/users/${user.id}/homework`, jsonPost(payload));
            form.reset(); close(); await load(); await onChanged();
            status.textContent = `Домашнее задание назначено, уведомление отправлено. ${status.textContent}`;
        } catch (error) { errorBox.textContent = error.message; }
        finally { saving = false; save.disabled = cancel.disabled = false; }
    });
    void load();
    return section;
}
