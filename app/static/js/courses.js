import { authFetch } from './course-auth.js';

const messages = Object.freeze({
    loadingError: 'Не удалось загрузить курсы.',
    emptyDescription: 'Описание курса пока не добавлено.',
    enrolled: 'В обучении',
    openCourse: 'Подробнее',
    continueCourse: 'Продолжить',
    fallbackTitle: 'Курс',
});

const elements = {
    loading: document.querySelector('[data-courses-loading]'),
    error: document.querySelector('[data-courses-error]'),
    errorMessage: document.querySelector('[data-courses-error-message]'),
    retry: document.querySelector('[data-courses-retry]'),
    empty: document.querySelector('[data-courses-empty]'),
    list: document.querySelector('[data-courses-list]'),
    search: document.querySelector('[data-course-search]'),
    filters: document.querySelectorAll('[data-course-filter]'),
    results: document.querySelector('[data-catalog-results]'),
    noResults: document.querySelector('[data-courses-no-results]'),
};

let allCourses = [];
let selectedFilter = 'all';
let coursesLoaded = false;

const getCourseUrl = (course) => `/${encodeURIComponent(course.slug)}`;

const getCourseSectionsUrl = (course) =>
    `/${encodeURIComponent(course.slug)}/sections`;

const fetchJson = async (url) => {
    const response = await authFetch(url);
    if (!response.ok) {
        throw new Error(`courses-load-failed:${response.status}`);
    }
    return response.json();
};

const loadCourseList = () => fetchJson('/api/courses');

const loadEnrollments = async () => {
    try {
        const enrollments = await fetchJson('/api/enrollments/me');
        return Array.isArray(enrollments) ? enrollments : [];
    } catch (error) {
        console.warn('Could not load enrollments.', error);
        return [];
    }
};

const setLoading = () => {
    coursesLoaded = false;
    elements.loading.hidden = false;
    elements.error.hidden = true;
    elements.empty.hidden = true;
    elements.list.replaceChildren();
    elements.noResults.hidden = true;
    elements.results.textContent = '';
};

const setError = (message) => {
    elements.loading.hidden = true;
    elements.empty.hidden = true;
    elements.error.hidden = false;
    elements.errorMessage.textContent = message;
    elements.list.replaceChildren();
};

const setEmpty = () => {
    elements.loading.hidden = true;
    elements.error.hidden = true;
    elements.empty.hidden = false;
    elements.list.replaceChildren();
};

const setContent = () => {
    elements.loading.hidden = true;
    elements.error.hidden = true;
    elements.empty.hidden = true;
};

const createMeta = (course) => {
    const meta = document.createElement('p');
    const items = [course.level, course.price_label].filter(Boolean);

    meta.className = 'courses-card__meta';
    meta.textContent = items.join(' · ');
    return meta;
};

const createCourseCard = (course, index) => {
    const isEnrolled = Boolean(course.is_enrolled);
    const article = document.createElement('article');
    const header = document.createElement('div');
    const title = document.createElement('h2');
    const badge = document.createElement('span');
    const description = document.createElement('p');
    const link = document.createElement('a');

    article.className = 'courses-card';
    const visual = document.createElement('div');
    visual.className = `courses-card__visual courses-card__visual--${index % 3}`;
    visual.setAttribute('aria-hidden', 'true');
    const symbol = document.createElement('span');
    symbol.textContent = ['</>', '{ }', '[ ]'][index % 3];
    const caption = document.createElement('span');
    caption.textContent = 'LEARN. PRACTICE. GROW.';
    visual.append(symbol, caption);
    if (course.icon_url) {
        const icon = document.createElement('img');
        icon.className = 'courses-card__icon';
        icon.alt = '';
        icon.loading = 'lazy';
        icon.addEventListener('error', () => {
            visual.classList.remove('courses-card__visual--image');
            visual.replaceChildren(symbol, caption);
        }, { once: true });
        visual.classList.add('courses-card__visual--image');
        visual.replaceChildren(icon);
        icon.src = course.icon_url;
    }
    article.classList.toggle('courses-card--enrolled', isEnrolled);

    header.className = 'courses-card__header';
    title.textContent = course.title || messages.fallbackTitle;
    header.append(title);

    if (isEnrolled) {
        badge.className = 'courses-card__badge';
        badge.textContent = messages.enrolled;
        header.append(badge);
    }

    description.className = 'courses-card__description';
    description.textContent =
        course.short_description || course.description || messages.emptyDescription;

    link.className = 'courses-card__link';
    link.classList.toggle('courses-card__link--primary', isEnrolled);
    link.href = course.slug
        ? isEnrolled
            ? getCourseSectionsUrl(course)
            : getCourseUrl(course)
        : '#';
    link.textContent = isEnrolled
        ? messages.continueCourse
        : messages.openCourse;

    article.append(visual, header, description, createMeta(course), link);
    return article;
};

const renderCourses = (courses) => {
    const fragment = document.createDocumentFragment();
    courses.forEach((course, index) => {
        fragment.append(createCourseCard(course, index));
    });
    elements.list.replaceChildren(fragment);
    setContent();
};

const applyFilters = () => {
    if (!coursesLoaded) return;
    const query = elements.search.value.trim().toLocaleLowerCase('ru');
    const visible = allCourses.filter((course) =>
        (selectedFilter !== 'enrolled' || course.is_enrolled) &&
        [course.title, course.short_description, course.description].filter(Boolean).join(' ').toLocaleLowerCase('ru').includes(query)
    );
    renderCourses(visible);
    elements.noResults.hidden = visible.length > 0;
    elements.results.textContent = `Найдено курсов: ${visible.length}`;
};

elements.search.addEventListener('input', applyFilters);
elements.filters.forEach((button) => button.addEventListener('click', () => {
    selectedFilter = button.dataset.courseFilter;
    elements.filters.forEach((filter) => filter.setAttribute('aria-pressed', String(filter === button)));
    applyFilters();
}));

const loadCourses = async () => {
    setLoading();

    try {
        const [courses, enrollments] = await Promise.all([
            loadCourseList(),
            loadEnrollments(),
        ]);
        const enrolledCourseIds = new Set(
            enrollments.map((enrollment) => enrollment.course_id)
        );
        const publishedCourses = Array.isArray(courses)
            ? courses
                .filter((course) => course.id && course.is_published !== false)
                .map((course) => ({
                    ...course,
                    is_enrolled: enrolledCourseIds.has(course.id),
                }))
            : [];

        allCourses = publishedCourses;
        coursesLoaded = true;
        if (publishedCourses.length === 0) {
            setEmpty();
            return;
        }

        applyFilters();
    } catch (error) {
        if (error instanceof Error && error.message === 'authentication-required') {
            return;
        }
        console.warn('Could not load courses.', error);
        setError(messages.loadingError);
    }
};

elements.retry?.addEventListener('click', loadCourses);
document.addEventListener('DOMContentLoaded', loadCourses);
