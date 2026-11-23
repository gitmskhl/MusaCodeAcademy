function updateIndicator(indicator, now) {
    // A due date has no time component: it stays current through the local day.
    const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    const dueDate = indicator.dataset.dueDate;
    let state = 'none';
    let label = indicator.dataset.hasHomework === 'true' ? 'Последнее ДЗ без срока сдачи' : 'ДЗ не назначалось';
    if (dueDate) {
        state = dueDate < today ? 'overdue' : 'upcoming';
        const formatted = dueDate.split('-').reverse().join('.');
        label = `Последнее ДЗ: ${state === 'overdue' ? 'срок прошёл' : 'срок не истёк'} · Сдать до ${formatted} включительно`;
    }
    indicator.className = `homework-deadline homework-deadline--${state}`;
    indicator.title = label;
    indicator.setAttribute('aria-label', label);
}

export function createUserIdWithHomework(user, now = new Date()) {
    const cell = document.createElement('span');
    cell.className = 'monitoring-user-id';
    const indicator = document.createElement('span');
    indicator.dataset.homeworkDeadline = '';
    indicator.dataset.hasHomework = String(!!user.latest_homework);
    indicator.dataset.dueDate = user.latest_homework?.due_date || '';
    indicator.setAttribute('role', 'img');
    updateIndicator(indicator, now);
    cell.append(indicator, document.createTextNode(String(user.id)));
    return cell;
}

export function refreshHomeworkDeadlines(root, now = new Date()) {
    root.querySelectorAll('[data-homework-deadline]').forEach(indicator => updateIndicator(indicator, now));
}
