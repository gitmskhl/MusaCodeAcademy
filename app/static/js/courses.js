import { authFetch } from './course-auth.js';

const messages = Object.freeze({
    loadingError: 'Не удалось загрузить курсы.',
    emptyDescription: 'Описание курса пока не добавлено.',
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

const fetchJson = async (url) => {
    const response = await authFetch(url);
    if (!response.ok) {
        throw new Error(`courses-load-failed:${response.status}`);
    }
    return response.json();
};

const loadCourseList = async () => {
    const urls = [
        '/api/courses',
        '/api/courses/',
        '/api/courses/admin',
    ];
    let lastError;

    for (const url of urls) {
        try {
            return await fetchJson(url);
        } catch (error) {
            lastError = error;
            console.warn(`Could not load courses from ${url}.`, error);
        }
    }

    throw lastError ?? new Error('courses-load-failed');
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

const createCourseCard = (course) => {
    const article = document.createElement('article');
    const title = document.createElement('h2');
    const description = document.createElement('p');
    const link = document.createElement('a');

    article.className = 'courses-card';
    title.textContent = course.title || 'Курс';
    description.textContent =
        course.short_description || course.description || messages.emptyDescription;

    link.className = 'courses-card__link';
    link.href = course.slug ? getCourseUrl(course) : '#';
    link.textContent = 'Открыть курс';

    article.append(title, description, link);
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
        const courses = await loadCourseList();
        const publishedCourses = Array.isArray(courses)
            ? courses.filter((course) => course.id && course.is_published !== false)
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
