function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
}

// Confirmation content is always rendered as text, including names and email.
function confirmationButton({ label, title, description, email, request, onSaved }) {
    const trigger = el('button', label, 'button button--danger');
    trigger.type = 'button';
    let opened = false;
    trigger.addEventListener('click', () => {
        if (opened) return;
        opened = true;
        const dialog = el('dialog', undefined, 'block-dialog');
        dialog.setAttribute('aria-label', title);
        const form = el('form', undefined, 'admin-form');
        form.append(el('h2', title), el('p', description));
        let confirmation;
        if (email) {
            const field = el('label', 'Для подтверждения введите email пользователя:', 'field');
            confirmation = el('input');
            confirmation.type = 'email';
            confirmation.required = true;
            confirmation.autocomplete = 'off';
            confirmation.spellcheck = false;
            field.append(confirmation);
            form.append(field);
        }
        const error = el('p', '', 'field-error');
        error.setAttribute('role', 'alert');
        const actions = el('div', undefined, 'form-actions');
        const cancel = el('button', 'Отмена', 'button button--ghost');
        cancel.type = 'button';
        cancel.autofocus = true;
        cancel.addEventListener('click', () => dialog.close());
        const submit = el('button', label, 'button button--danger');
        submit.type = 'submit';
        actions.append(cancel, submit);
        form.append(error, actions);
        dialog.append(form);
        let saving = false;
        dialog.addEventListener('cancel', event => { if (saving) event.preventDefault(); });
        dialog.addEventListener('close', () => {
            opened = false;
            dialog.remove();
        });
        form.addEventListener('submit', async event => {
            event.preventDefault();
            if (saving) return;
            error.textContent = '';
            if (confirmation && confirmation.value.trim() !== email) {
                error.textContent = 'Email не совпадает. Введите email удаляемого пользователя.';
                return;
            }
            saving = true;
            cancel.disabled = submit.disabled = true;
            if (confirmation) confirmation.disabled = true;
            try {
                await request();
                dialog.close();
                await onSaved();
            } catch (failure) {
                error.textContent = failure.message;
            } finally {
                saving = false;
                cancel.disabled = submit.disabled = false;
                if (confirmation) confirmation.disabled = false;
            }
        });
        document.body.append(dialog);
        dialog.showModal();
    });
    return trigger;
}

export function createDeleteUserButton({ user, adminId, api, onDeleted }) {
    const trigger = confirmationButton({
        label: 'Удалить пользователя', title: 'Удалить пользователя навсегда?', email: user.email,
        description: `${user.first_name} ${user.last_name} (${user.email}). Аккаунт, записи на курсы, решения, прогресс и история AI-помощи будут удалены без возможности отмены.`,
        request: () => api(`/api/admin/users/${user.id}`, { method: 'DELETE' }),
        onSaved: onDeleted,
    });
    trigger.disabled = user.id === adminId;
    if (trigger.disabled) trigger.title = 'Нельзя удалить собственный аккаунт';
    return trigger;
}

export function createEnrollmentAction({ user, course, api, onSaved }) {
    const path = `/api/admin/users/${user.id}/courses/${course.id}`;
    if (course.enrolled) return confirmationButton({
        label: 'Отписать', title: 'Отписать пользователя от курса?',
        description: `${user.first_name} ${user.last_name} (${user.email}) — «${course.title}». Курс исчезнет из кабинета пользователя. Решения и прогресс сохранятся для повторной записи.`,
        request: () => api(path, { method: 'DELETE' }),
        onSaved: () => onSaved('Пользователь отписан от курса. Решения и прогресс сохранены.'),
    });
    const wrapper = el('div');
    const trigger = el('button', 'Записать снова', 'button button--ghost');
    trigger.type = 'button';
    const error = el('p', '', 'field-error');
    error.setAttribute('role', 'alert');
    let saving = false;
    trigger.addEventListener('click', async () => {
        if (saving) return;
        saving = trigger.disabled = true;
        error.textContent = '';
        try {
            await api(path, { method: 'PUT' });
            await onSaved('Пользователь снова записан на курс.');
        } catch (failure) {
            error.textContent = failure.message;
        } finally {
            saving = trigger.disabled = false;
        }
    });
    wrapper.append(trigger, error);
    return wrapper;
}

export function createEnrollmentForm({ user, courses, api, onSaved }) {
    const form = el('form', undefined, 'monitoring-enrollment-form');
    const field = el('label', 'Записать на курс', 'field');
    const select = el('select');
    select.required = true;
    const available = courses.filter(course => !user.courses.some(item => item.id === course.id && item.enrolled));
    const placeholder = el('option', available.length ? 'Выберите курс' : 'Нет доступных для записи курсов');
    placeholder.value = '';
    select.append(placeholder);
    for (const course of available) {
        const option = el('option', `${course.title}${course.is_published ? '' : ' (черновик)'}`);
        option.value = String(course.id);
        select.append(option);
    }
    const submit = el('button', 'Записать', 'button button--primary');
    submit.type = 'submit';
    select.disabled = submit.disabled = available.length === 0;
    field.append(select);
    const error = el('p', '', 'field-error');
    error.setAttribute('role', 'alert');
    form.append(field, submit, error);
    let saving = false;
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (saving || !select.value || !available.some(course => String(course.id) === select.value)) return;
        saving = true;
        select.disabled = submit.disabled = true;
        error.textContent = '';
        try {
            await api(`/api/admin/users/${user.id}/courses/${select.value}`, { method: 'PUT' });
            await onSaved('Пользователь записан на курс.');
        } catch (failure) {
            error.textContent = failure.message;
        } finally {
            saving = false;
            select.disabled = submit.disabled = false;
        }
    });
    return form;
}
