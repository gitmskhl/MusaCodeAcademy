import { requireCurrentUser } from './course-auth.js';
import { api, el, jsonPost, pager } from './notifications.js';

const form = document.querySelector('[data-notification-form]');
const mode = form.elements.mode;
const search = form.elements.search;
const picker = document.querySelector('[data-student-picker]');
const results = document.querySelector('[data-student-results]');
const selectedList = document.querySelector('[data-selected-students]');
const searchStatus = document.querySelector('[data-search-status]');
const searchPagination = document.querySelector('[data-search-pagination]');
const preview = document.querySelector('[data-recipient-preview]');
const errorBox = document.querySelector('[data-form-error]');
const success = document.querySelector('[data-form-success]');
const submit = document.querySelector('[data-send]');
const selected = new Map();
let searchVersion = 0;
let previewed;
let saving = false;
let timer;
let lastPage;

function invalidate() {
    previewed = null;
    preview.hidden = true;
    submit.textContent = 'Проверить получателей';
    submit.disabled = false;
    success.hidden = true;
    errorBox.textContent = '';
}
function renderSelected() {
    document.querySelector('[data-selected-count]').textContent = String(selected.size);
    selectedList.replaceChildren(...[...selected.values()].map(user => {
        const chip = el('button', `${user.first_name} ${user.last_name} (${user.email}) ×`, 'button button--ghost');
        chip.type = 'button';
        chip.setAttribute('aria-label', `Убрать: ${user.first_name} ${user.last_name}, ${user.email}`);
        chip.addEventListener('click', () => { selected.delete(user.id); invalidate(); renderSelected(); renderResults(); });
        return chip;
    }));
}
function renderResults() {
    if (!lastPage) return;
    results.replaceChildren(...lastPage.items.map(user => {
        const row = el('label', null, 'recipient-option');
        const input = el('input');
        input.type = mode.value === 'single' ? 'radio' : 'checkbox';
        input.name = 'recipient-choice';
        input.value = user.id;
        input.checked = selected.has(user.id);
        input.addEventListener('change', () => {
            if (mode.value === 'single') selected.clear();
            if (input.checked) selected.set(user.id, user);
            else selected.delete(user.id);
            invalidate(); renderSelected(); renderResults();
        });
        row.append(input, el('span', `${user.first_name} ${user.last_name} · ${user.email}`));
        return row;
    }));
}
async function searchStudents(page = 1) {
    const version = ++searchVersion;
    searchStatus.textContent = 'Поиск…';
    try {
        const params = new URLSearchParams({ q: search.value, page });
        const data = await api(`/api/admin/notification-recipients?${params}`);
        if (version !== searchVersion) return;
        lastPage = data;
        searchStatus.textContent = data.total ? `Найдено учеников: ${data.total}` : 'Ученики не найдены.';
        renderResults();
        searchPagination.replaceChildren(pager(data, searchStudents));
    } catch (error) { if (version === searchVersion) searchStatus.textContent = error.message; }
}
mode.addEventListener('change', () => {
    selected.clear(); renderSelected(); invalidate();
    picker.hidden = mode.value === 'all';
    if (!picker.hidden) void searchStudents();
});
search.addEventListener('input', () => {
    ++searchVersion;
    clearTimeout(timer);
    timer = setTimeout(() => void searchStudents(), 250);
});
form.elements.title.addEventListener('input', invalidate);
form.elements.text.addEventListener('input', invalidate);
form.addEventListener('submit', async event => {
    event.preventDefault();
    if (saving) return;
    const selection = { recipient_mode: mode.value === 'all' ? 'all' : 'selected', recipient_ids: [...selected.keys()] };
    const payload = { ...selection, title: form.elements.title.value.trim(), text: form.elements.text.value.trim() };
    if (!payload.title || !payload.text) { errorBox.textContent = 'Заполните заголовок и текст.'; return; }
    if (mode.value !== 'all' && !selected.size) { errorBox.textContent = 'Выберите хотя бы одного ученика.'; return; }
    const fingerprint = JSON.stringify(payload);
    const sending = previewed === fingerprint;
    saving = true;
    const controls = [...form.querySelectorAll('input, textarea, select, button')];
    controls.forEach(control => { control.disabled = true; });
    errorBox.textContent = '';
    let noRecipients = false;
    try {
        if (sending) {
            const data = await api('/api/admin/notifications', jsonPost(payload));
            form.reset(); selected.clear(); renderSelected(); picker.hidden = true;
            invalidate();
            success.textContent = `Уведомление отправлено. Получателей: ${data.count}.`;
            success.hidden = false;
        } else {
            const data = await api('/api/admin/notifications/preview', jsonPost(selection));
            preview.textContent = `Количество получателей: ${data.count}. ${data.count ? 'Проверьте сообщение и нажмите «Отправить уведомление».' : 'Нет учеников для отправки.'}`;
            preview.hidden = false;
            previewed = data.count ? fingerprint : null;
            noRecipients = !data.count;
            submit.textContent = 'Отправить уведомление';
        }
    } catch (error) { errorBox.textContent = error.message; invalidatePreview(); }
    finally { saving = false; controls.forEach(control => { control.disabled = false; }); submit.disabled = noRecipients; }
});
function invalidatePreview() { previewed = null; preview.hidden = true; submit.textContent = 'Проверить получателей'; }

async function init() {
    try {
        const user = await requireCurrentUser();
        if (user.role !== 'admin') { document.querySelector('[data-loading]').textContent = 'Доступ разрешён только администратору.'; return; }
        document.querySelector('[data-loading]').hidden = true;
        document.querySelector('[data-shell]').hidden = false;
    } catch (error) { if (error.message !== 'authentication-required') document.querySelector('[data-loading]').textContent = error.message; }
}
void init();
