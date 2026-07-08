import { authFetch } from './course-auth.js';

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

const messages = Object.freeze({
    loadingError: '\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0440\u0430\u0437\u0434\u0435\u043b\u044b \u043a\u0443\u0440\u0441\u0430.',
    emptyDescription: '\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u0440\u0430\u0437\u0434\u0435\u043b\u0430 \u043f\u043e\u043a\u0430 \u043d\u0435 \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u043e.',
    emptySections: '\u0420\u0430\u0437\u0434\u0435\u043b\u044b \u043a\u0443\u0440\u0441\u0430 \u0441\u043a\u043e\u0440\u043e \u043f\u043e\u044f\u0432\u044f\u0442\u0441\u044f.',
    openSection: '\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u0440\u0430\u0437\u0434\u0435\u043b',
    section: '\u0420\u0430\u0437\u0434\u0435\u043b',
});

const getCourseSlug = () => {
    const templateSlug = elements.root?.dataset.courseSlug?.trim();
    if (templateSlug) {
        return templateSlug;
    }

    const [, slug] = window.location.pathname.match(/^\/([^/]+)\/sections\/?$/) || [];
    return slug ? decodeURIComponent(slug) : '';
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

const getOrderedSections = (course) => {
    const sections = Array.isArray(course.sections) ? course.sections : [];
    return [...sections].sort((first, second) => {
        const firstOrder = Number(first.order);
        const secondOrder = Number(second.order);
        return (
            (Number.isFinite(firstOrder) ? firstOrder : 0) -
                (Number.isFinite(secondOrder) ? secondOrder : 0) ||
            Number(first.id) - Number(second.id)
        );
    });
};

const countLessons = (sections) =>
    sections.reduce((total, section) => {
        const lessons = Array.isArray(section.lessons) ? section.lessons : [];
        return total + lessons.length;
    }, 0);

const getLessonCountLabel = (count) =>
    `${count} ${pluralizeRu(
        count,
        '\u0443\u0440\u043e\u043a',
        '\u0443\u0440\u043e\u043a\u0430',
        '\u0443\u0440\u043e\u043a\u043e\u0432'
    )}`;

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

const createLessonPreview = (lessons) => {
    const list = document.createElement('ul');
    list.className = 'course-section-card__lessons';

    lessons.slice(0, 3).forEach((lesson) => {
        const item = document.createElement('li');
        item.textContent = lesson.title;
        list.append(item);
    });

    return list;
};

const createSectionCard = (section, index, courseSlug) => {
    const lessons = Array.isArray(section.lessons) ? section.lessons : [];
    const link = document.createElement('a');
    const meta = document.createElement('p');
    const title = document.createElement('h2');
    const description = document.createElement('p');
    const footer = document.createElement('span');

    link.className = 'course-section-card';
    link.href =
        `/${encodeURIComponent(courseSlug)}/sections/` +
        `${encodeURIComponent(section.id)}/lessons`;

    meta.className = 'course-section-card__meta';
    meta.textContent = `${messages.section} ${index + 1} - ${getLessonCountLabel(lessons.length)}`;

    title.textContent = section.title;

    description.className = 'course-section-card__description';
    description.textContent = section.description || messages.emptyDescription;

    footer.className = 'course-section-card__action';
    footer.textContent = messages.openSection;

    link.append(meta, title, description);

    if (lessons.length > 0) {
        link.append(createLessonPreview(lessons));
    }

    link.append(footer);
    return link;
};

const renderProgress = (sections) => {
    const lessonsCount = countLessons(sections);
    elements.progressPercent.textContent = '0%';
    elements.progressBar.style.width = '0%';
    elements.progressCount.textContent = getLessonCountLabel(lessonsCount);
};

const renderSections = (course, sections) => {
    elements.sections.replaceChildren();

    if (sections.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'course-program__empty';
        empty.textContent = messages.emptySections;
        elements.sections.append(empty);
        return;
    }

    const fragment = document.createDocumentFragment();
    sections.forEach((section, index) => {
        fragment.append(createSectionCard(section, index, course.slug));
    });
    elements.sections.append(fragment);
};

const renderCourse = (course) => {
    const sections = getOrderedSections(course);

    document.title = `${course.title} | Musa Code Academy`;
    elements.title.textContent = course.title;
    elements.description.textContent = course.short_description || course.description || '';
    renderProgress(sections);
    renderSections(course, sections);
    setContent();
};

const loadCourseSections = async () => {
    const courseSlug = getCourseSlug();
    if (!courseSlug) {
        setError(messages.loadingError);
        return;
    }

    setLoading();

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

        setError(messages.loadingError);
    }
};

elements.retry?.addEventListener('click', loadCourseSections);
document.addEventListener('DOMContentLoaded', loadCourseSections);
