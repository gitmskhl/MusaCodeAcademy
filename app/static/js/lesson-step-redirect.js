import { authFetch, requireToken } from './course-auth.js';

const root = document.querySelector('[data-lesson-step-redirect]');

const showError = () => {
    const message = document.querySelector('[data-redirect-error]');
    if (message) {
        message.hidden = false;
    }
};

const init = async () => {
    try {
        requireToken();

        const lessonId = root?.dataset.lessonId;
        const courseSlug = root?.dataset.courseSlug?.trim();
        if (!lessonId || !courseSlug) {
            showError();
            return;
        }

        const params = new URLSearchParams({ course_slug: courseSlug });
        const response = await authFetch(
            `/api/lessons/${encodeURIComponent(lessonId)}/first-step?${params}`
        );
        if (!response.ok) {
            showError();
            return;
        }

        const stepId = await response.json();
        window.location.replace(
            `/${encodeURIComponent(courseSlug)}/steps/${encodeURIComponent(stepId)}`
        );
    } catch (error) {
        if (error?.message !== 'authentication-required') {
            showError();
        }
    }
};

init();
