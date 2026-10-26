import { authFetch, requireCurrentUser } from './course-auth.js';
import { confirmUnenrollment } from './course-unenroll.js';

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
    catalog: document.querySelector('[data-dashboard-catalog]'),
    overview: document.querySelector('[data-dashboard-overview]'),
    listHeading: document.querySelector('[data-dashboard-list-heading]'),
    otherCourseCount: document.querySelector('[data-other-course-count]'),
    activeCount: document.querySelector('[data-active-course-count]'),
    completedSteps: document.querySelector('[data-completed-step-count]'),
    completedCourses: document.querySelector('[data-completed-course-count]'),
    currentUnenroll: document.querySelector('[data-current-course-unenroll]'),
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
            const name = displayName.split(' ')[0] || displayName
            elements.greetingTitle.textContent = `С возвращением, ${name}!`;
            document.querySelector('[data-app-profile-button]').textContent = name.charAt(0).toUpperCase();
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

const loadCoursesProgress = async () => {
    try {
        const response = await authFetch('/api/progress/me/courses');
        if (!response.ok) {
            return new Map();
        }

        const progress = await response.json();
        return new Map(
            (Array.isArray(progress) ? progress : [])
                .map((item) => [item.course_id, item])
        );
    } catch {
        return new Map();
    }
};

const getProgressDetails = (progress) => ({
    percent: clampProgress(progress?.percent),
    completedStepCount: Number(progress?.completed_step_count) || 0,
    totalStepCount: Number(progress?.total_step_count) || 0,
    completedLessonCount: Number(progress?.completed_lesson_count) || 0,
    totalLessonCount: Number(progress?.total_lesson_count) || 0,
    lastStepId: Number(progress?.last_step_id) || null,
    lastVisitedAt: progress?.last_visited_at || null,
});

const getCourseContinueUrl = (course) =>
    course.slug && course.lastStepId
        ? `/${encodeURIComponent(course.slug)}/steps/${encodeURIComponent(course.lastStepId)}`
        : course.slug
            ? getCourseUrl(course)
            : '#';

const rememberEnrolledCourses = (courses) => {
    const storableCourses = courses
        .filter((course) => course.id)
        .map((course) => ({
            id: course.id,
            slug: course.slug,
            title: course.title,
            short_description: course.short_description,
            description: course.description,
            progress: course.progressData,
        }));

    localStorage.setItem(ENROLLED_COURSES_KEY, JSON.stringify(storableCourses));
};

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

const applyCoursesProgress = (courses, progressByCourseId) =>
    courses.map((course) => {
        const progressData = progressByCourseId.get(course.id) ?? course.progressData;
        const details = getProgressDetails(progressData);

        return {
            ...course,
            progress: details.percent,
            progressData,
            completedStepCount: details.completedStepCount,
            totalStepCount: details.totalStepCount,
            completedLessonCount: details.completedLessonCount,
            totalLessonCount: details.totalLessonCount,
            lastStepId: details.lastStepId,
            lastVisitedAt: details.lastVisitedAt,
            action: details.percent >= 100 ? 'Повторить' : details.percent > 0 ? messages.continue : messages.start,
            href: details.percent >= 100 ? getCourseUrl(course) : getCourseContinueUrl({
                ...course,
                lastStepId: details.lastStepId,
            }),
        };
    });

const setLoading = () => {
    elements.loading.hidden = false;
    elements.error.hidden = true;
    elements.empty.hidden = true;
    elements.currentCourse.hidden = true;
    elements.overview.hidden = true;
    elements.listHeading.hidden = true;
    elements.catalog.hidden = true;
    elements.courseList.replaceChildren();
};

const setError = (message) => {
    elements.loading.hidden = true;
    elements.empty.hidden = true;
    elements.currentCourse.hidden = true;
    elements.overview.hidden = true;
    elements.listHeading.hidden = true;
    elements.catalog.hidden = true;
    elements.error.hidden = false;
    elements.errorMessage.textContent = message;
    elements.courseList.replaceChildren();
};

const setEmpty = () => {
    elements.loading.hidden = true;
    elements.error.hidden = true;
    elements.empty.hidden = false;
    elements.currentCourse.hidden = true;
    elements.overview.hidden = true;
    elements.listHeading.hidden = true;
    elements.catalog.hidden = true;
    elements.courseList.replaceChildren();
};

const setContent = () => {
    elements.loading.hidden = true;
    elements.error.hidden = true;
    elements.empty.hidden = true;
    elements.catalog.hidden = false;
    elements.overview.hidden = false;
};

const createCourseCard = (course) => {
    const article = document.createElement('article');
    const header = document.createElement('div');
    const title = document.createElement('h3');
    const icon = document.createElement('span');
    icon.className = 'student-course-icon';
    icon.textContent = '</>';
    icon.setAttribute('aria-hidden', 'true');
    const description = document.createElement('p');
    const progress = document.createElement('div');
    const meta = document.createElement('div');
    const label = document.createElement('span');
    const value = document.createElement('span');
    const bar = document.createElement('span');
    const barValue = document.createElement('span');
    const details = document.createElement('p');
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
    details.className = 'course-card__details';
    details.textContent =
        `${course.completedStepCount ?? 0} / ` +
        `${course.totalStepCount ?? 0} шагов`;
    progress.append(meta, bar, details);

    link.className = 'course-card__button';
    link.href = course.href;
    link.textContent = course.action;

    const actions = document.createElement('div');
    actions.className = 'course-card__actions';
    const unenroll = document.createElement('button');
    unenroll.type = 'button';
    unenroll.className = 'course-unenroll-button';
    unenroll.textContent = 'Отписаться';
    unenroll.setAttribute('aria-label', `Отписаться от курса «${course.title}»`);
    unenroll.addEventListener('click', () => confirmUnenrollment(course, loadDashboard));
    actions.append(link, unenroll);
    article.append(icon, header, progress, actions);
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
    elements.currentCourseProgress.setAttribute('aria-valuenow', String(course.progress));
    elements.currentCourseStatus.textContent =
        `${course.completedStepCount ?? 0} / ` +
        `${course.totalStepCount ?? 0} шагов завершено`;
    elements.currentCourseDescription.textContent = course.description;
    elements.currentCourseLink.href = course.href;
    elements.currentCourseLink.textContent = course.progress >= 100
        ? 'Повторить курс ↗'
        : course.action === messages.start ? 'Начать обучение ↗' : 'Продолжить обучение ↗';
    elements.currentUnenroll.setAttribute('aria-label', `Отписаться от курса «${course.title}»`);
    elements.currentUnenroll.onclick = () => confirmUnenrollment(course, loadDashboard);
    elements.currentCourse.hidden = false;
};

const getVisitedAtTime = (course) => {
    const time = Date.parse(course.lastVisitedAt || '');
    return Number.isFinite(time) ? time : 0;
};

const getCurrentCourse = (courses) =>
    [...courses].sort((first, second) => {
        const completionDiff = Number(first.progress >= 100) - Number(second.progress >= 100);
        if (completionDiff) return completionDiff;
        const visitedDiff = getVisitedAtTime(second) - getVisitedAtTime(first);
        if (visitedDiff !== 0) {
            return visitedDiff;
        }
        return (second.completedStepCount ?? 0) - (first.completedStepCount ?? 0);
    })[0] ?? courses[0];

const renderCourses = (courses) => {
    const current = getCurrentCourse(courses);
    const others = courses.filter((course) => course.id !== current.id);
    const fragment = document.createDocumentFragment();
    others.forEach((course) => {
        fragment.append(createCourseCard(course));
    });
    elements.courseList.replaceChildren(fragment);
    renderCurrentCourse(current);
    elements.activeCount.textContent = courses.filter((course) => course.progress < 100).length;
    elements.completedCourses.textContent = courses.filter((course) => course.progress >= 100).length;
    elements.completedSteps.textContent = courses.reduce((total, course) => total + (course.completedStepCount || 0), 0);
    elements.otherCourseCount.textContent = `Курсов: ${others.length}`;
    setContent();
    elements.listHeading.hidden = others.length === 0;
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

        const progressByCourseId = await loadCoursesProgress();
        courses = applyCoursesProgress(courses, progressByCourseId);

        rememberEnrolledCourses(courses);

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
