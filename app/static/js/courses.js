import { authFetch } from './course-auth.js';

const messages = Object.freeze({
    loadingError: 'Не удалось загрузить курсы.',
    emptyDescription: 'Описание курса пока не добавлено.',
    enrolled: 'Вы записаны',
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
};

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
    elements.loading.hidden = false;
    elements.error.hidden = true;
    elements.empty.hidden = true;
    elements.list.replaceChildren();
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

const createCourseCard = (course) => {
    const isEnrolled = Boolean(course.is_enrolled);
    const article = document.createElement('article');
    const header = document.createElement('div');
    const title = document.createElement('h2');
    const badge = document.createElement('span');
    const description = document.createElement('p');
    const link = document.createElement('a');

    article.className = 'courses-card';
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

    article.append(header, description, createMeta(course), link);
    return article;
};

const renderCourses = (courses) => {
    const fragment = document.createDocumentFragment();
    courses.forEach((course) => {
        fragment.append(createCourseCard(course));
    });
    elements.list.replaceChildren(fragment);
    setContent();
};

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

        if (publishedCourses.length === 0) {
            setEmpty();
            return;
        }

        renderCourses(publishedCourses);
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
