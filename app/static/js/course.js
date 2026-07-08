import { authFetch } from './course-auth.js';

const elements = {
    root: document.querySelector('[data-course-page]'),
    title: document.querySelector('[data-course-title]'),
    description: document.querySelector('[data-course-description]'),
    meta: document.querySelector('[data-course-meta]'),
    outcomes: document.querySelector('[data-course-outcomes]'),
    program: document.querySelector('[data-course-program]'),
    lessonsCount: document.querySelector('[data-course-lessons-count]'),
    sectionsCount: document.querySelector('[data-course-sections-count]'),
    level: document.querySelector('[data-course-level]'),
    price: document.querySelector('[data-course-price]'),
    enrollButton: document.querySelector('.course-enroll-button'),
};

const state = {
    course: null,
    isSubmittingEnrollment: false,
};

const labels = Object.freeze({
    enroll: '\u0417\u0430\u043f\u0438\u0441\u0430\u0442\u044c\u0441\u044f \u043d\u0430 \u043a\u0443\u0440\u0441',
    enrolling: '\u0417\u0430\u043f\u0438\u0441\u044b\u0432\u0430\u0435\u043c...',
    continue: '\u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c \u043a\u0443\u0440\u0441',
    enrollFailed: '\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u043f\u0438\u0441\u0430\u0442\u044c\u0441\u044f',
});

const getCourseSlug = () => {
    const templateSlug = elements.root?.dataset.courseSlug?.trim();
    if (templateSlug) {
        return templateSlug;
    }

    const [, slug] = window.location.pathname.match(/^\/([^/]+)\/?$/) || [];
    return slug ? decodeURIComponent(slug) : '';
};

const getCourseSectionsUrl = (course) =>
    course?.slug ? `/${encodeURIComponent(course.slug)}/sections` : '/dashboard';

const openCourseStart = (course) => {
    window.location.assign(getCourseSectionsUrl(course));
};

const setEnrollmentButton = ({ busy = false, error = false } = {}) => {
    if (!elements.enrollButton) {
        return;
    }

    const isEnrolled = Boolean(state.course?.is_enrolled);
    elements.enrollButton.disabled = busy;
    elements.enrollButton.setAttribute('aria-busy', String(busy));

    if (busy) {
        elements.enrollButton.textContent = labels.enrolling;
    } else if (error) {
        elements.enrollButton.textContent = labels.enrollFailed;
    } else {
        elements.enrollButton.textContent = isEnrolled ? labels.continue : labels.enroll;
    }
};

const pluralizeRu = (count, one, few, many) => {
    const abs = Math.abs(count);
    const last = abs % 10;
    const lastTwo = abs % 100;

    if (last === 1 && lastTwo !== 11) {
        return one;
    }

    if ([2, 3, 4].includes(last) && ![12, 13, 14].includes(lastTwo)) {
        return few;
    }

    return many;
};

const countLessons = (sections) =>
    sections.reduce((total, section) => {
        const lessons = Array.isArray(section.lessons) ? section.lessons : [];
        return total + lessons.length;
    }, 0);

const getCourseStats = (course) => {
    const sections = Array.isArray(course.sections) ? course.sections : [];
    const lessonsCount = Number.isFinite(Number(course.lessons_count))
        ? Number(course.lessons_count)
        : countLessons(sections);
    const sectionsCount = Number.isFinite(Number(course.sections_count))
        ? Number(course.sections_count)
        : sections.length;

    return {
        lessonsCount,
        sectionsCount,
    };
};

const createMetaItem = (value) => {
    const item = document.createElement('span');
    item.textContent = value;
    return item;
};

const createOutcomeItem = (outcome) => {
    const item = document.createElement('div');
    const check = document.createElement('span');
    const text = document.createElement('span');

    item.className = 'course-outcome';
    check.className = 'course-outcome__check';
    check.setAttribute('aria-hidden', 'true');
    check.textContent = '\u2713';
    text.textContent = outcome;
    item.append(check, text);

    return item;
};

const createLessonItem = (lesson) => {
    const item = document.createElement('li');
    item.textContent = typeof lesson === 'string' ? lesson : lesson.title;
    return item;
};

const createProgramSection = (section, index) => {
    const item = document.createElement('article');
    const button = document.createElement('button');
    const title = document.createElement('span');
    const icon = document.createElement('span');
    const body = document.createElement('div');
    const inner = document.createElement('div');
    const list = document.createElement('ul');
    const contentId = `course-program-section-${section.id ?? index + 1}`;
    const isOpen = index === 0;
    const lessons = Array.isArray(section.lessons) ? section.lessons : [];

    item.className = 'course-accordion__item';
    item.classList.toggle('is-open', isOpen);

    button.className = 'course-accordion__button';
    button.type = 'button';
    button.setAttribute('aria-expanded', String(isOpen));
    button.setAttribute('aria-controls', contentId);

    icon.className = 'course-accordion__icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = '\u25be';

    title.className = 'course-accordion__title';
    title.textContent = section.title;

    body.className = 'course-accordion__body';
    body.id = contentId;

    inner.className = 'course-accordion__inner';
    list.className = 'course-lessons';

    if (lessons.length === 0) {
        const empty = document.createElement('li');
        empty.textContent = 'Уроки скоро появятся';
        list.append(empty);
    } else {
        lessons.forEach((lesson) => {
            list.append(createLessonItem(lesson));
        });
    }

    button.append(icon, title);
    inner.append(list);
    body.append(inner);
    item.append(button, body);

    button.addEventListener('click', () => {
        const nextOpenState = !item.classList.contains('is-open');
        item.classList.toggle('is-open', nextOpenState);
        button.setAttribute('aria-expanded', String(nextOpenState));
    });

    return item;
};

const renderMeta = (course, stats) => {
    const lessonWord = pluralizeRu(stats.lessonsCount, 'урок', 'урока', 'уроков');
    const sectionWord = pluralizeRu(stats.sectionsCount, 'раздел', 'раздела', 'разделов');

    elements.meta.replaceChildren(
        createMetaItem(`${stats.lessonsCount} ${lessonWord}`),
        createMetaItem(`${stats.sectionsCount} ${sectionWord}`),
        createMetaItem(course.level),
        createMetaItem(course.price_label),
    );
};

const renderOutcomes = (outcomes) => {
    const items = Array.isArray(outcomes) ? outcomes : [];

    if (items.length === 0) {
        elements.outcomes.replaceChildren(
            createOutcomeItem('Подробные результаты обучения скоро появятся'),
        );
        return;
    }

    elements.outcomes.replaceChildren(...items.map(createOutcomeItem));
};

const renderProgram = (sections) => {
    const items = Array.isArray(sections) ? sections : [];

    if (items.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'course-program__empty';
        empty.textContent = 'Программа курса скоро появится.';
        elements.program.replaceChildren(empty);
        return;
    }

    elements.program.replaceChildren(...items.map(createProgramSection));
};

const renderCourse = (course) => {
    const stats = getCourseStats(course);
    state.course = course;

    document.title = `${course.title} | Musa Code Academy`;
    elements.title.textContent = course.title;
    elements.description.textContent = course.short_description || course.description || '';
    elements.lessonsCount.textContent = stats.lessonsCount;
    elements.sectionsCount.textContent = stats.sectionsCount;
    elements.level.textContent = course.level;
    elements.price.textContent = course.price_label;

    if (elements.enrollButton) {
        elements.enrollButton.textContent = course.is_enrolled
            ? 'Продолжить курс'
            : 'Записаться на курс';
    }

    setEnrollmentButton();
    renderMeta(course, stats);
    renderOutcomes(course.outcomes);
    renderProgram(course.sections);
};

const setError = (message) => {
    elements.title.textContent = 'Курс недоступен';
    elements.description.textContent = message;
    elements.meta.replaceChildren();
    elements.outcomes.replaceChildren();
    elements.program.replaceChildren();
    elements.lessonsCount.textContent = '0';
    elements.sectionsCount.textContent = '0';
    elements.level.textContent = '—';
    elements.price.textContent = '—';
};

const enrollInCourse = async () => {
    if (!state.course || state.isSubmittingEnrollment) {
        return;
    }

    if (state.course.is_enrolled) {
        openCourseStart(state.course);
        return;
    }

    state.isSubmittingEnrollment = true;
    setEnrollmentButton({ busy: true });

    try {
        const response = await authFetch(
            `/api/courses/${encodeURIComponent(state.course.id)}/enroll`,
            { method: 'POST' }
        );

        if (!response.ok && response.status !== 409) {
            throw new Error('enrollment-failed');
        }

        state.course = {
            ...state.course,
            is_enrolled: true,
        };
        setEnrollmentButton();
        openCourseStart(state.course);
    } catch (error) {
        if (error instanceof Error && error.message === 'authentication-required') {
            return;
        }

        setEnrollmentButton({ error: true });
        window.setTimeout(() => setEnrollmentButton(), 2400);
    } finally {
        state.isSubmittingEnrollment = false;
        if (elements.enrollButton) {
            elements.enrollButton.disabled = false;
            elements.enrollButton.setAttribute('aria-busy', 'false');
        }
    }
};

const loadCourse = async () => {
    const courseSlug = getCourseSlug();
    if (!courseSlug) {
        setError('Не удалось определить, какой курс нужно открыть.');
        return;
    }

    elements.title.textContent = 'Загрузка курса...';
    elements.description.textContent = '';

    try {
        const response = await authFetch(`/api/courses/slug/${encodeURIComponent(courseSlug)}`);
        if (!response.ok) {
            throw new Error('course-load-failed');
        }

        renderCourse(await response.json());
    } catch (error) {
        if (error instanceof Error && error.message === 'authentication-required') {
            return;
        }

        setError('Курс не найден или пока недоступен.');
    }
};

elements.enrollButton?.addEventListener('click', enrollInCourse);
document.addEventListener('DOMContentLoaded', loadCourse);
