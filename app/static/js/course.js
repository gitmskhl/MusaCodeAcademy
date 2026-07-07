import { authFetch } from './course-auth.js';

(function () {
    const statusMap = {
        available: {
            className: 'lesson-row--available',
            icon: '\u203a',
            label: 'available',
        },
    };

    const elements = {
        root: document.querySelector('[data-course-page]'),
        loading: document.querySelector('[data-course-loading]'),
        error: document.querySelector('[data-course-error]'),
        errorMessage: document.querySelector('[data-course-error-message]'),
        retry: document.querySelector('[data-course-retry]'),
        content: document.querySelector('[data-course-content]'),
        title: document.querySelector('[data-course-title]'),
        description: document.querySelector('[data-course-description]'),
        progressBar: document.querySelector('[data-course-progress-bar]'),
        progressPercent: document.querySelector('[data-course-progress-percent]'),
        progressCount: document.querySelector('[data-course-progress-count]'),
        sections: document.querySelector('[data-sections]'),
    };

    const getCourseSlug = () => {
        const templateSlug = elements.root?.dataset.courseSlug?.trim();
        if (templateSlug) {
            return templateSlug;
        }

        const [, slug] = window.location.pathname.match(/^\/([^/]+)\/?$/) || [];
        return slug ? decodeURIComponent(slug) : '';
    };

    const getOrderNumber = (item, fallbackIndex) => {
        const order = Number(item.order);
        return Number.isFinite(order) ? order + 1 : fallbackIndex + 1;
    };

    const pluralizeLessons = (count) => {
        const abs = Math.abs(count);
        const last = abs % 10;
        const lastTwo = abs % 100;

        if (last === 1 && lastTwo !== 11) {
            return 'урок';
        }

        if ([2, 3, 4].includes(last) && ![12, 13, 14].includes(lastTwo)) {
            return 'урока';
        }

        return 'уроков';
    };

    const getSectionStatus = (index) => {
        const statuses = [
            {
                className: 'section-card--current',
                icon: '\u25b6',
                label: 'Продолжить',
            },
            {
                className: 'section-card--not-started',
                icon: '\u25cb',
                label: 'Не начато',
            },
            {
                className: 'section-card--completed',
                icon: '\u2713',
                label: 'Завершено',
            },
        ];

        return statuses[index % statuses.length];
    };

    const setLoading = () => {
        elements.loading.hidden = false;
        elements.error.hidden = true;
        elements.content.hidden = true;
    };

    const setError = (message) => {
        elements.loading.hidden = true;
        elements.content.hidden = true;
        elements.error.hidden = false;
        elements.errorMessage.textContent = message;
    };

    const setContent = () => {
        elements.loading.hidden = true;
        elements.error.hidden = true;
        elements.content.hidden = false;
    };

    const createLessonRow = (lesson, index, courseSlug) => {
        const status = statusMap.available;
        const row = document.createElement('button');
        const number = document.createElement('span');
        const title = document.createElement('span');
        const icon = document.createElement('span');
        const lessonNumber = getOrderNumber(lesson, index);

        row.type = 'button';
        row.className = `lesson-row ${status.className}`;
        row.dataset.lessonId = lesson.id;
        row.setAttribute('aria-label', `Урок ${lessonNumber}. ${lesson.title}`);

        number.className = 'lesson-row__number';
        number.textContent = `Урок ${lessonNumber}.`;

        title.className = 'lesson-row__title';
        title.textContent = lesson.title;

        icon.className = 'lesson-row__status';
        icon.setAttribute('aria-hidden', 'true');
        icon.textContent = status.icon;

        row.append(number, title, icon);
        row.addEventListener('click', () => {
            window.location.href =
                `/${encodeURIComponent(courseSlug)}/lessons/${encodeURIComponent(lesson.id)}/steps`;
        });

        return row;
    };

    const createSectionCard = (section, index, isOpen, courseSlug) => {
        const card = document.createElement('article');
        const toggle = document.createElement('button');
        const icon = document.createElement('span');
        const titleWrap = document.createElement('span');
        const heading = document.createElement('span');
        const meta = document.createElement('span');
        const count = document.createElement('span');
        const statusBadge = document.createElement('span');
        const body = document.createElement('div');
        const inner = document.createElement('div');
        const lessonList = document.createElement('div');
        const lessons = Array.isArray(section.lessons) ? section.lessons : [];
        const contentId = `section-${section.id}-lessons`;
        const status = getSectionStatus(index);

        card.className = `section-card ${status.className}`;
        card.classList.toggle('is-open', isOpen);

        toggle.type = 'button';
        toggle.className = 'section-card__toggle';
        toggle.setAttribute('aria-expanded', String(isOpen));
        toggle.setAttribute('aria-controls', contentId);

        icon.className = 'section-card__icon';
        icon.setAttribute('aria-hidden', 'true');
        icon.textContent = '\u203a';

        titleWrap.className = 'section-card__title';

        heading.className = 'section-card__heading';
        heading.textContent = section.title;

        meta.className = 'section-card__meta';

        count.className = 'section-card__count';
        count.textContent = `${lessons.length} ${pluralizeLessons(lessons.length)}`;

        statusBadge.className = 'section-card__status';
        statusBadge.innerHTML = `<span aria-hidden="true">${status.icon}</span>${status.label}`;

        body.className = 'section-card__body';
        body.id = contentId;

        inner.className = 'section-card__inner';
        lessonList.className = 'lesson-list';

        if (lessons.length === 0) {
            const empty = document.createElement('p');
            empty.className = 'lesson-list__empty';
            empty.textContent = 'В этом разделе пока нет уроков.';
            lessonList.append(empty);
        } else {
            lessons.forEach((lesson, lessonIndex) => {
                lessonList.append(createLessonRow(lesson, lessonIndex, courseSlug));
            });
        }

        meta.append(count, statusBadge);
        titleWrap.append(heading, meta);
        toggle.append(icon, titleWrap);
        inner.append(lessonList);
        body.append(inner);
        card.append(toggle, body);

        toggle.addEventListener('click', () => {
            const nextOpenState = !card.classList.contains('is-open');
            card.classList.toggle('is-open', nextOpenState);
            toggle.setAttribute('aria-expanded', String(nextOpenState));
        });

        return card;
    };

    const updateCourseProgress = (sections) => {
        const totalLessons = sections.reduce((sum, section) => {
            const lessons = Array.isArray(section.lessons) ? section.lessons : [];
            return sum + lessons.length;
        }, 0);
        const total = totalLessons || 36;
        const completed = Math.max(0, Math.min(total, Math.round(total * 0.43)));
        const percentage = total ? Math.round((completed / total) * 100) : 0;

        if (elements.progressBar) {
            elements.progressBar.style.width = `${percentage}%`;
        }

        if (elements.progressPercent) {
            elements.progressPercent.textContent = `${percentage}%`;
        }

        if (elements.progressCount) {
            elements.progressCount.textContent =
                `${completed} из ${total} ${pluralizeLessons(total)}`;
        }
    };

    const render = (course) => {
        const sections = Array.isArray(course.sections) ? course.sections : [];
        const slug = course.slug || getCourseSlug();

        document.title = course.title;
        elements.title.textContent = course.title;
        elements.description.textContent = course.short_description || course.description || '';
        elements.sections.replaceChildren();
        updateCourseProgress(sections);

        if (sections.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'course-empty';
            empty.textContent = 'В этом курсе пока нет разделов.';
            elements.sections.append(empty);
        } else {
            const fragment = document.createDocumentFragment();
            sections.forEach((section, index) => {
                fragment.append(createSectionCard(section, index, index === 0, slug));
            });
            elements.sections.append(fragment);
        }

        setContent();
    };

    const loadCourse = async () => {
        const courseSlug = getCourseSlug();
        if (!courseSlug) {
            setError('Could not determine which course to open.');
            return;
        }

        setLoading();

        try {
            const response = await authFetch(`/api/courses/slug/${encodeURIComponent(courseSlug)}`);
            if (!response.ok) {
                throw new Error('course-load-failed');
            }

            render(await response.json());
        } catch (error) {
            if (error instanceof Error && error.message === 'authentication-required') {
                return;
            }

            setError('Could not load this course. It may be unavailable or unpublished.');
        }
    };

    elements.retry?.addEventListener('click', loadCourse);
    document.addEventListener('DOMContentLoaded', loadCourse);
})();
