(function () {
    const STATUS = Object.freeze({
        completed: {
            className: 'lesson-card--completed',
            icon: '✓',
            label: 'Пройден',
        },
        in_progress: {
            className: 'lesson-card--current',
            icon: '▶',
            label: 'В процессе',
        },
        not_started: {
            className: '',
            icon: '○',
            label: 'Не начат',
        },
    });

    const elements = {
        root: document.querySelector('[data-lesson-page]'),
        loading: document.querySelector('[data-page-loading]'),
        error: document.querySelector('[data-page-error]'),
        errorMessage: document.querySelector('[data-error-message]'),
        retry: document.querySelector('[data-retry]'),
        content: document.querySelector('[data-page-content]'),
        backLink: document.querySelector('[data-back-link]'),
        title: document.querySelector('[data-section-title]'),
        description: document.querySelector('[data-section-description]'),
        progressPercent: document.querySelector('[data-progress-percent]'),
        progressTrack: document.querySelector('[data-progress-track]'),
        progressBar: document.querySelector('[data-progress-bar]'),
        progressLabel: document.querySelector('[data-progress-label]'),
        lessonCount: document.querySelector('[data-lesson-count]'),
        lessonList: document.querySelector('[data-lesson-list]'),
        emptyState: document.querySelector('[data-empty-state]'),
    };

    const getPathContext = () => {
        const match = window.location.pathname.match(
            /^\/([^/]+)\/sections\/(\d+)\/lessons\/?$/
        );
        return {
            courseSlug: match ? decodeURIComponent(match[1]) : '',
            sectionId: match ? match[2] : '',
        };
    };

    const getContext = () => {
        const path = getPathContext();
        return {
            courseSlug: elements.root?.dataset.courseSlug?.trim() || path.courseSlug,
            sectionId: elements.root?.dataset.sectionId?.trim() || path.sectionId,
        };
    };

    const getStatus = (lesson) =>
        STATUS[lesson.status] ?? STATUS.not_started;

    const pluralizeLessons = (count) => {
        const mod10 = count % 10;
        const mod100 = count % 100;
        if (mod10 === 1 && mod100 !== 11) {
            return `${count} урок`;
        }
        if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
            return `${count} урока`;
        }
        return `${count} уроков`;
    };

    const createLessonCard = (lesson, index, courseSlug) => {
        const status = getStatus(lesson);
        const card = document.createElement('a');
        const statusIcon = document.createElement('span');
        const body = document.createElement('div');
        const meta = document.createElement('p');
        const title = document.createElement('h3');
        const description = document.createElement('p');
        const actions = document.createElement('div');
        const badge = document.createElement('span');
        const chevron = document.createElement('span');

        card.className = ['lesson-card', status.className].filter(Boolean).join(' ');
        card.href = `/${encodeURIComponent(courseSlug)}/lessons/${encodeURIComponent(lesson.id)}/steps`;
        card.setAttribute('aria-label', `Открыть урок «${lesson.title}»`);

        statusIcon.className = 'lesson-card__status-icon';
        statusIcon.setAttribute('aria-hidden', 'true');
        statusIcon.textContent = status.icon;

        body.className = 'lesson-card__body';
        meta.className = 'lesson-card__meta';
        const order = Number(lesson.order);
        meta.textContent = `Урок ${
            Number.isFinite(order) ? order + 1 : index + 1
        }`;
        title.className = 'lesson-card__title';
        title.textContent = lesson.title;
        description.className = 'lesson-card__description';
        description.textContent = lesson.description || 'Описание урока пока не добавлено.';
        body.append(meta, title, description);

        actions.className = 'lesson-card__actions';
        badge.className = 'lesson-card__badge';
        badge.textContent = status.label;
        actions.append(badge);

        if (status === STATUS.in_progress) {
            const continueButton = document.createElement('span');
            continueButton.className = 'lesson-card__continue';
            continueButton.textContent = 'Продолжить';
            actions.append(continueButton);
        }

        chevron.className = 'lesson-card__chevron';
        chevron.setAttribute('aria-hidden', 'true');
        chevron.textContent = '›';
        actions.append(chevron);

        card.append(statusIcon, body, actions);
        return card;
    };

    const updateProgress = (lessons) => {
        const completed = lessons.filter(
            (lesson) => lesson.status === 'completed'
        ).length;
        const percentage = lessons.length
            ? Math.round((completed / lessons.length) * 100)
            : 0;

        elements.progressPercent.textContent = `${percentage}%`;
        elements.progressLabel.textContent =
            `${completed} из ${lessons.length} уроков пройдено`;
        elements.progressTrack.setAttribute('aria-valuenow', String(percentage));
        elements.progressBar.style.width = `${percentage}%`;
    };

    const render = (section, lessons, courseSlug) => {
        const orderedLessons = [...lessons].sort(
            (first, second) =>
                Number(first.order) - Number(second.order) ||
                Number(first.id) - Number(second.id)
        );

        document.title = `${section.title} — уроки`;
        elements.title.textContent = section.title;
        elements.description.textContent =
            section.description || 'Изучите материалы раздела по порядку.';
        elements.lessonCount.textContent = pluralizeLessons(orderedLessons.length);
        elements.backLink.href = `/${encodeURIComponent(courseSlug)}`;
        elements.lessonList.replaceChildren();
        elements.emptyState.hidden = orderedLessons.length !== 0;

        const fragment = document.createDocumentFragment();
        orderedLessons.forEach((lesson, index) => {
            fragment.append(createLessonCard(lesson, index, courseSlug));
        });
        elements.lessonList.append(fragment);
        updateProgress(orderedLessons);
    };

    const showError = (message) => {
        elements.loading.hidden = true;
        elements.content.hidden = true;
        elements.error.hidden = false;
        elements.errorMessage.textContent = message;
    };

    const loadPage = async () => {
        const { courseSlug, sectionId } = getContext();
        if (!elements.root || !courseSlug || !/^\d+$/.test(sectionId)) {
            showError('Не удалось определить выбранный раздел.');
            return;
        }

        elements.loading.hidden = false;
        elements.error.hidden = true;
        elements.content.hidden = true;

        try {
            const [sectionResponse, lessonsResponse] = await Promise.all([
                fetch(`/api/sections/${encodeURIComponent(sectionId)}`),
                fetch(`/api/sections/${encodeURIComponent(sectionId)}/lessons`),
            ]);

            if (!sectionResponse.ok || !lessonsResponse.ok) {
                throw new Error('request-failed');
            }

            const [section, lessons] = await Promise.all([
                sectionResponse.json(),
                lessonsResponse.json(),
            ]);

            render(section, Array.isArray(lessons) ? lessons : [], courseSlug);
            elements.loading.hidden = true;
            elements.content.hidden = false;
        } catch {
            showError('Не удалось загрузить уроки. Попробуйте обновить страницу.');
        }
    };

    elements.retry?.addEventListener('click', loadPage);
    document.addEventListener('DOMContentLoaded', loadPage);
})();
