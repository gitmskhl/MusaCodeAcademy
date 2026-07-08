import { authFetch, requireCurrentUser } from './course-auth.js';

const messages = Object.freeze({
    loadingError: 'Не удалось загрузить ваши курсы.',
    emptyDescription: 'Описание курса пока не добавлено.',
    notStarted: 'Обучение еще не начато',
    start: 'Начать',
    continue: 'Продолжить',
    progressLabel: 'Прогресс',
});

const elements = {
    greetingTitle: document.querySelector('[data-dashboard-greeting-title]'),
    currentCourse: document.querySelector('[data-current-course]'),
    currentCourseTitle: document.querySelector('[data-current-course-title]'),
    currentCoursePercent: document.querySelector('[data-current-course-percent]'),
    currentCourseProgress: document.querySelector('[data-current-course-progress]'),
    currentCourseProgressBar: document.querySelector('[data-current-course-progress-bar]'),
    currentCourseStatus: document.querySelector('[data-current-course-status]'),
    currentCourseDescription: document.querySelector('[data-current-course-description]'),
    currentCourseLink: document.querySelector('[data-current-course-link]'),
    loading: document.querySelector('[data-dashboard-loading]'),
    error: document.querySelector('[data-dashboard-error]'),
    errorMessage: document.querySelector('[data-dashboard-error-message]'),
    retry: document.querySelector('[data-dashboard-retry]'),
    empty: document.querySelector('[data-dashboard-empty]'),
    courseList: document.querySelector('[data-course-list]'),
};

const ENROLLED_COURSES_KEY = 'musa_code_academy_enrolled_courses';

const getUserDisplayName = (user) => {
    const firstName = typeof user?.first_name === 'string' ? user.first_name.trim() : '';
    const lastName = typeof user?.last_name === 'string' ? user.last_name.trim() : '';

    return [firstName, lastName].filter(Boolean).join(' ');
};

const loadGreeting = async () => {
    try {
        const displayName = getUserDisplayName(await requireCurrentUser());
        if (displayName && elements.greetingTitle) {
            elements.greetingTitle.textContent = `Добро пожаловать, ${displayName}! 👋`;
        }
    } catch (error) {
        if (error instanceof Error && error.message === 'authentication-required') {
            return;
        }
    }
};

const clampProgress = (value) => {
    const progress = Number(value ?? 0);
    if (!Number.isFinite(progress)) {
        return 0;
    }
    return Math.max(0, Math.min(100, Math.round(progress)));
};

const getCourseUrl = (course) => `/${encodeURIComponent(course.slug)}/sections`;

const getStoredEnrolledCourses = () => {
    try {
        const stored = JSON.parse(localStorage.getItem(ENROLLED_COURSES_KEY) || '[]');
        return Array.isArray(stored) ? stored : [];
    } catch {
        return [];
    }
};

const rememberEnrolledCourses = (courses) => {
    const storableCourses = courses
        .filter((course) => course.id)
        .map((course) => ({
            id: course.id,
            slug: course.slug,
            title: course.title,
            short_description: course.short_description,
            description: course.description,
        }));

    localStorage.setItem(ENROLLED_COURSES_KEY, JSON.stringify(storableCourses));
};

const mapStoredCourseToDashboardCourse = (course) => ({
    id: course.id,
    slug: course.slug,
    title: course.title ?? '\u041a\u0443\u0440\u0441',
    short_description: course.short_description,
    description: course.short_description || course.description || messages.emptyDescription,
    progress: 0,
    action: messages.start,
    href: course.slug ? getCourseUrl(course) : '#',
});

const mapCourseInfoToDashboardCourse = (course) => ({
    id: course.id,
    slug: course.slug,
    title: course.title ?? '\u041a\u0443\u0440\u0441',
    short_description: course.short_description,
    description: course.short_description || course.description || messages.emptyDescription,
    progress: 0,
    action: messages.start,
    href: course.slug ? getCourseUrl(course) : '#',
});

const mapEnrollmentToCourse = (enrollment) => {
    const course = enrollment.course ?? {};
    const progress = clampProgress(enrollment.progress_percent);
    const courseId = course.id ?? enrollment.course_id ?? enrollment.id;

    return {
        id: courseId,
        slug: course.slug,
        title: course.title ?? 'Курс',
        description: course.short_description || course.description || messages.emptyDescription,
        short_description: course.short_description,
        progress,
        action: progress > 0 ? messages.continue : messages.start,
        href: course.slug ? getCourseUrl(course) : '#',
    };
};

const setLoading = () => {
    elements.loading.hidden = false;
    elements.error.hidden = true;
    elements.empty.hidden = true;
    elements.currentCourse.hidden = true;
    elements.courseList.replaceChildren();
};

const setError = (message) => {
    elements.loading.hidden = true;
    elements.empty.hidden = true;
    elements.currentCourse.hidden = true;
    elements.error.hidden = false;
    elements.errorMessage.textContent = message;
    elements.courseList.replaceChildren();
};

const setEmpty = () => {
    elements.loading.hidden = true;
    elements.error.hidden = true;
    elements.empty.hidden = false;
    elements.currentCourse.hidden = true;
    elements.courseList.replaceChildren();
};

const setContent = () => {
    elements.loading.hidden = true;
    elements.error.hidden = true;
    elements.empty.hidden = true;
};

const createCourseCard = (course) => {
    const article = document.createElement('article');
    const header = document.createElement('div');
    const title = document.createElement('h3');
    const description = document.createElement('p');
    const progress = document.createElement('div');
    const meta = document.createElement('div');
    const label = document.createElement('span');
    const value = document.createElement('span');
    const bar = document.createElement('span');
    const barValue = document.createElement('span');
    const link = document.createElement('a');

    article.className = 'course-card';

    title.textContent = course.title;
    description.textContent = course.description;
    header.append(title, description);

    progress.className = 'course-card__progress';
    progress.setAttribute(
        'aria-label',
        `Прогресс курса ${course.progress} процентов`
    );

    meta.className = 'course-card__meta';
    label.textContent = messages.progressLabel;
    value.textContent = `${course.progress}%`;
    meta.append(label, value);

    bar.className = 'course-card__bar';
    barValue.className = 'course-card__value';
    barValue.style.width = `${course.progress}%`;
    bar.append(barValue);
    progress.append(meta, bar);

    link.className = 'course-card__button';
    link.href = course.href;
    link.textContent = course.action;

    article.append(header, progress, link);
    return article;
};

const renderCurrentCourse = (course) => {
    elements.currentCourseTitle.textContent = course.title;
    elements.currentCoursePercent.textContent = `${course.progress}%`;
    elements.currentCourseProgress.setAttribute(
        'aria-label',
        `Прогресс курса ${course.progress} процентов`
    );
    elements.currentCourseProgressBar.style.width = `${course.progress}%`;
    elements.currentCourseStatus.textContent =
        course.progress > 0 ? `${course.progress}% завершено` : messages.notStarted;
    elements.currentCourseDescription.textContent = course.description;
    elements.currentCourseLink.href = course.href;
    elements.currentCourseLink.textContent = course.action === messages.start
        ? 'Начать обучение'
        : 'Продолжить обучение';
    elements.currentCourse.hidden = false;
};

const renderCourses = (courses) => {
    const fragment = document.createDocumentFragment();
    courses.forEach((course) => {
        fragment.append(createCourseCard(course));
    });
    elements.courseList.replaceChildren(fragment);
    renderCurrentCourse(courses[0]);
    setContent();
};

const loadEnrolledCoursesFromCoursePages = async () => {
    const coursesResponse = await authFetch('/api/courses');
    if (!coursesResponse.ok) {
        return [];
    }

    const publishedCourses = await coursesResponse.json();
    if (!Array.isArray(publishedCourses) || publishedCourses.length === 0) {
        return [];
    }

    const coursePages = await Promise.all(
        publishedCourses
            .filter((course) => course.slug)
            .map(async (course) => {
                try {
                    const response = await authFetch(
                        `/api/courses/slug/${encodeURIComponent(course.slug)}`
                    );
                    return response.ok ? response.json() : null;
                } catch {
                    return null;
                }
            })
    );

    return coursePages
        .filter((course) => course?.is_enrolled)
        .map(mapCourseInfoToDashboardCourse)
        .filter((course) => course.id);
};

const loadDashboard = async () => {
    setLoading();

    try {
        const response = await authFetch('/api/enrollments/me');
        if (!response.ok) {
            throw new Error('dashboard-load-failed');
        }

        const enrollments = await response.json();
        let courses = Array.isArray(enrollments)
            ? enrollments.map(mapEnrollmentToCourse).filter((course) => course.id)
            : [];

        if (courses.length === 0) {
            courses = await loadEnrolledCoursesFromCoursePages();
        }

        if (courses.length === 0) {
            courses = getStoredEnrolledCourses()
                .map(mapStoredCourseToDashboardCourse)
                .filter((course) => course.id);
        }

        if (courses.length > 0) {
            rememberEnrolledCourses(courses);
        }

        if (courses.length === 0) {
            setEmpty();
            return;
        }

        renderCourses(courses);
    } catch (error) {
        if (error instanceof Error && error.message === 'authentication-required') {
            return;
        }
        setError(messages.loadingError);
    }
};

elements.retry?.addEventListener('click', loadDashboard);
document.addEventListener('DOMContentLoaded', () => {
    loadGreeting();
    loadDashboard();
});
