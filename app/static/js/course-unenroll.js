import { authFetch } from './course-auth.js';

const ENROLLED_COURSES_KEY = 'musa_code_academy_enrolled_courses';

export const confirmUnenrollment = (course, onSuccess) => {
    if (document.querySelector('[data-unenroll-dialog]')) return;

    const dialog = document.createElement('dialog');
    dialog.className = 'unenroll-dialog';
    dialog.dataset.unenrollDialog = '';
    dialog.setAttribute('aria-labelledby', 'unenroll-title');
    dialog.setAttribute('aria-describedby', 'unenroll-description');
    dialog.innerHTML = `
        <span class="unenroll-dialog__icon" aria-hidden="true">↗</span>
        <h2 id="unenroll-title">Отписаться от курса?</h2>
        <p class="unenroll-dialog__course"></p>
        <p id="unenroll-description">Курс исчезнет из твоего кабинета. Прогресс сохранится — можно будет записаться снова и продолжить обучение.</p>
        <p class="unenroll-dialog__error" role="alert" hidden></p>
        <div class="unenroll-dialog__actions">
            <button type="button" data-unenroll-cancel autofocus>Остаться</button>
            <button type="button" data-unenroll-confirm>Отписаться</button>
        </div>`;
    dialog.querySelector('.unenroll-dialog__course').textContent = course.title;
    const cancel = dialog.querySelector('[data-unenroll-cancel]');
    const confirm = dialog.querySelector('[data-unenroll-confirm]');
    const errorMessage = dialog.querySelector('[role="alert"]');
    let busy = false;
    const trigger = document.activeElement;

    cancel.addEventListener('click', () => dialog.close());
    dialog.addEventListener('cancel', (event) => {
        if (busy) event.preventDefault();
    });
    dialog.addEventListener('close', () => dialog.remove(), { once: true });
    confirm.addEventListener('click', async () => {
        if (busy) return;
        busy = true;
        cancel.disabled = true;
        confirm.disabled = true;
        confirm.textContent = 'Отписываем…';
        dialog.setAttribute('aria-busy', 'true');
        errorMessage.hidden = true;

        try {
            const response = await authFetch(`/api/courses/${encodeURIComponent(course.id)}/enroll`, { method: 'DELETE' });
            if (!response.ok && response.status !== 404) throw new Error('unenrollment-failed');
        } catch (error) {
            if (error.message === 'authentication-required') {
                dialog.close();
                return;
            }
            busy = false;
            cancel.disabled = false;
            confirm.disabled = false;
            confirm.textContent = 'Повторить';
            dialog.setAttribute('aria-busy', 'false');
            errorMessage.textContent = 'Не удалось отписаться. Проверь подключение и попробуй ещё раз.';
            errorMessage.hidden = false;
            return;
        }

        // A stale browser cache must not restore a cancelled enrollment.
        try {
            const stored = JSON.parse(localStorage.getItem(ENROLLED_COURSES_KEY) || '[]');
            const remaining = Array.isArray(stored)
                ? stored.filter((item) => item.id !== course.id)
                : [];
            localStorage.setItem(ENROLLED_COURSES_KEY, JSON.stringify(remaining));
        } catch {
            // The server is authoritative even when browser storage is unavailable.
        }
        dialog.close();
        await onSuccess();
        if (!trigger?.isConnected) {
            const heading = document.querySelector('main h1');
            heading?.setAttribute('tabindex', '-1');
            heading?.focus({ preventScroll: true });
        }
    });

    document.body.append(dialog);
    dialog.showModal();
};
