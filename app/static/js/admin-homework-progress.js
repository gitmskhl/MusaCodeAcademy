import { el, homeworkDetails } from './notifications.js';

const taskStatuses = {
    solved: 'Решено', attempted: 'Есть попытки, не решено', checking: 'Проверяется', not_started: 'Нет отправок',
};

export function createLatestHomeworkSection({ user, api, submissionTable, pager }) {
    const section = el('section', null, 'section-block homework-progress');
    const heading = el('div', null, 'monitoring-section-heading');
    const refresh = el('button', 'Обновить', 'button button--ghost');
    refresh.type = 'button';
    heading.append(el('h2', 'Последнее ДЗ'), refresh);
    const status = el('p', '', 'notification-feedback');
    status.setAttribute('role', 'status');
    const content = el('div', null, 'homework-progress__content');
    section.append(heading, status, content);
    let request = 0;
    let currentPage = 1;

    function render(data) {
        content.replaceChildren();
        if (!data.homework) {
            status.textContent = 'Домашние задания пока не назначены.';
            return;
        }
        const open = el('a', 'Открыть домашнее задание', 'homework-open');
        open.href = data.steps?.[0]?.url || data.homework.url;
        content.append(el('h3', data.homework.title), homeworkDetails(data.homework), open);
        if (data.unavailable_reason) {
            status.textContent = data.unavailable_reason;
            return;
        }
        status.textContent = `${data.course_title} · ${data.lesson_title}`;
        const stats = el('div', null, 'monitoring-stats');
        [[data.solved_tasks, 'Решено задач'], [data.total_tasks - data.solved_tasks, 'Осталось решить'],
            [data.submissions.total, 'Всего отправок по ДЗ']].forEach(([value, label]) => {
            const stat = el('div', null, 'monitoring-stat');
            stat.append(el('strong', value), el('span', label));
            stats.append(stat);
        });
        const progress = el('progress', null, 'homework-progress__bar');
        progress.max = data.total_tasks || 1;
        progress.value = data.solved_tasks;
        progress.setAttribute('aria-label', `Решено задач: ${data.solved_tasks} из ${data.total_tasks}`);
        content.append(stats, progress,
            el('p', 'Учитываются все отправки, в том числе до назначения ДЗ. Задача решена, если есть хотя бы одно принятое решение. Теория учитывается отдельно по отметке о прохождении.', 'monitoring-muted'));
        content.append(el('h3', 'Степы домашнего задания'));
        const list = el('ol', null, 'homework-progress__steps');
        data.steps.forEach(step => {
            const row = el('li', null, `homework-progress__step homework-progress__step--${step.status}`);
            const link = el('a', `${step.position}. ${step.title}`, 'homework-progress__step-link');
            link.href = step.url;
            const details = el('div', null, 'homework-progress__step-details');
            const label = step.task_id === null
                ? `Теория · ${step.status === 'completed' ? 'Пройдена' : 'Не пройдена'}`
                : taskStatuses[step.status];
            details.append(el('span', label, 'homework-progress__state'));
            if (step.task_id !== null) {
                const attempts = el('a', `Отправки: ${step.submissions_count}`, 'monitoring-link');
                attempts.href = `/admin/submissions?user_id=${user.id}&task_id=${step.task_id}`;
                details.append(attempts);
            }
            row.append(link, details);
            list.append(row);
        });
        content.append(list);
        if (!data.steps.length) content.append(el('p', 'В этом уроке пока нет степов.', 'monitoring-muted'));
        if (!data.total_tasks && data.steps.length) content.append(el('p', 'В этом ДЗ только теория — задач для отправки решений нет.', 'monitoring-muted'));
        content.append(el('h3', 'Все отправки по последнему ДЗ'));
        if (data.submissions.total) content.append(submissionTable(data.submissions.items), pager(data.submissions, load));
        else content.append(el('p', 'Ученик ещё не отправлял решения задач этого ДЗ.', 'monitoring-muted'));
    }

    async function load(page = 1) {
        const version = ++request;
        refresh.disabled = true;
        section.setAttribute('aria-busy', 'true');
        status.textContent = 'Загружаем статистику последнего ДЗ…';
        try {
            const data = await api(`/api/admin/users/${user.id}/homework/latest-progress?page=${page}&page_size=25`);
            if (version !== request) return;
            const lastPage = Math.max(1, Math.ceil(data.submissions.total / data.submissions.page_size));
            if (page > lastPage) return await load(lastPage);
            currentPage = page;
            render(data);
        } catch (error) {
            if (version !== request) return;
            content.replaceChildren();
            status.textContent = error.message;
        } finally {
            if (version === request) {
                refresh.disabled = false;
                section.setAttribute('aria-busy', 'false');
            }
        }
    }
    refresh.addEventListener('click', () => void load(currentPage));
    void load();
    return { element: section, reload: () => load() };
}
