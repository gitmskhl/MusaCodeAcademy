import { getStepBlocks } from './step-renderer/layout-renderers.js';
import { registerImageSource } from './step-renderer/image-sources.js';
import { renderStep } from './step-renderer/step-renderer.js';
import { authFetch, requireToken } from './course-auth.js';

const locales = Object.freeze({
    ru: {
        documentTitle: 'Материал урока',
        stepDocumentTitle: '{title} — Материал урока',
        backToLesson: '← К списку уроков',
        stepTitle: 'Название шага',
        progress: '{current} / {total}',
        contentLoading: 'Загружаем материал…',
        contentEmpty: 'В этом шаге пока нет материалов.',
        contentLoadError: 'Не удалось загрузить материал шага.',
        navigationLabel: 'Навигация по шагам',
        previousStep: 'Предыдущий',
        nextStep: 'Следующий',
    },
});

const getLocale = () => {
    const language = document.documentElement.lang.split('-', 1)[0];
    return locales[language] ?? locales.ru;
};

const format = (template, values) =>
    Object.entries(values).reduce(
        (result, [key, value]) =>
            result.replaceAll(`{${key}}`, String(value)),
        template
    );

const messages = getLocale();

const elements = {
    root: document.querySelector('[data-step-viewer]'),
    title: document.querySelector('[data-step-title]'),
    progress: document.querySelector('[data-step-progress]'),
    completeToggle: document.querySelector('[data-step-complete-toggle]'),
    content: document.querySelector('[data-step-content]'),
    placeholder: document.querySelector('[data-content-placeholder]'),
    backToLesson: document.querySelector('[data-back-to-lesson]'),
    navigation: document.querySelector('[data-step-navigation]'),
    previousStep: document.querySelector('[data-previous-step]'),
    nextStep: document.querySelector('[data-next-step]'),
    drawer: document.querySelector('[data-step-drawer]'),
    drawerToggle: document.querySelector('[data-step-drawer-toggle]'),
    drawerBackdrop: document.querySelector('[data-step-drawer-backdrop]'),
    drawerTitle: document.querySelector('[data-step-drawer-title]'),
    drawerList: document.querySelector('[data-step-drawer-list]'),
    drawerMessage: document.querySelector('[data-step-drawer-message]'),
};

const state = {
    currentStepId: null,
    lesson: null,
    progress: null,
    isProgressSaving: false,
};

const setDrawerOpen = (isOpen) => {
    document.body.classList.toggle('is-step-drawer-open', isOpen);
    elements.drawerToggle.setAttribute('aria-expanded', String(isOpen));
    elements.drawerToggle.setAttribute(
        'aria-label',
        isOpen ? 'Закрыть навигацию по шагам' : 'Открыть навигацию по шагам'
    );
    elements.drawer.setAttribute('aria-hidden', String(!isOpen));

    if (isOpen) {
        elements.drawer.setAttribute('tabindex', '-1');
        elements.drawer.focus();
    } else {
        elements.drawer.removeAttribute('tabindex');
    }
};

const initDrawer = () => {
    if (!elements.drawer || !elements.drawerToggle || !elements.drawerBackdrop) {
        return;
    }

    elements.drawerToggle.addEventListener('click', () => {
        const isOpen = elements.drawerToggle.getAttribute('aria-expanded') === 'true';
        setDrawerOpen(!isOpen);
    });
    elements.drawerBackdrop.addEventListener('click', () => {
        setDrawerOpen(false);
        elements.drawerToggle.focus();
    });
    document.addEventListener('keydown', (event) => {
        if (
            event.key === 'Escape' &&
            elements.drawerToggle.getAttribute('aria-expanded') === 'true'
        ) {
            setDrawerOpen(false);
            elements.drawerToggle.focus();
        }
    });
};

const showDrawerMessage = (message, { error = false } = {}) => {
    elements.drawerList.replaceChildren();
    elements.drawerMessage.textContent = message;
    elements.drawerMessage.hidden = false;
    elements.drawerMessage.classList.toggle(
        'step-drawer__message--error',
        error
    );
};

const getStepUrl = (stepId) => {
    const courseSlug = elements.root.dataset.courseSlug.trim();
    return `/${encodeURIComponent(courseSlug)}/steps/${encodeURIComponent(stepId)}`;
};

const setLessonListLink = (sectionId) => {
    const courseSlug = elements.root.dataset.courseSlug.trim();
    elements.backToLesson.href =
        `/${encodeURIComponent(courseSlug)}/sections/` +
        `${encodeURIComponent(sectionId)}/lessons`;
    elements.backToLesson.removeAttribute('aria-disabled');
};

const getCompletedStepIds = () =>
    new Set(
        Array.isArray(state.progress?.completed_step_ids)
            ? state.progress.completed_step_ids
            : []
    );

const renderDrawerSteps = (steps, currentStepId) => {
    elements.drawerList.replaceChildren();
    elements.drawerMessage.hidden = true;
    elements.drawerMessage.classList.remove('step-drawer__message--error');

    if (steps.length === 0) {
        showDrawerMessage('В этом уроке пока нет шагов.');
        return;
    }

    const fragment = document.createDocumentFragment();
    const completedStepIds = getCompletedStepIds();
    steps.forEach((step) => {
        const isCurrent = step.id === currentStepId;
        const isCompleted = completedStepIds.has(step.id);
        const item = document.createElement('li');
        const link = document.createElement('a');
        const status = document.createElement('span');
        const title = document.createElement('span');

        item.className = 'step-drawer__item';
        link.className = 'step-drawer__link';
        link.href = getStepUrl(step.id);
        link.dataset.drawerStepId = String(step.id);
        link.classList.toggle('is-completed', isCompleted);
        if (isCurrent) {
            link.setAttribute('aria-current', 'step');
        }

        status.className = 'step-drawer__status';
        status.setAttribute('aria-hidden', 'true');
        title.textContent = step.title;
        status.textContent = isCompleted ? '✓' : isCurrent ? '●' : '○';

        link.append(status, title);
        item.append(link);
        fragment.append(item);
    });
    elements.drawerList.append(fragment);
};

const renderDrawer = (lesson, currentStepId) => {
    setLessonListLink(lesson.section_id);
    elements.drawerTitle.textContent = lesson.title;
    renderDrawerSteps(
        Array.isArray(lesson.steps) ? lesson.steps : [],
        currentStepId
    );
};

const renderProgressState = () => {
    if (!elements.completeToggle || state.currentStepId === null) {
        return;
    }

    const isCompleted = getCompletedStepIds().has(state.currentStepId);

    elements.completeToggle.hidden = false;
    elements.completeToggle.disabled = state.isProgressSaving;
    elements.completeToggle.classList.toggle('is-completed', isCompleted);
    elements.completeToggle.textContent = isCompleted
        ? 'Шаг завершен'
        : 'Завершить шаг';

    if (state.lesson) {
        renderDrawer(state.lesson, state.currentStepId);
    }
};

const loadLessonProgress = async (lessonId) => {
    const response = await authFetch(
        `/api/progress/lessons/${encodeURIComponent(lessonId)}`
    );
    if (!response.ok) {
        return null;
    }
    return response.json();
};

const updateLocalProgress = (stepId, isCompleted) => {
    const completedIds = getCompletedStepIds();
    if (isCompleted) {
        completedIds.add(stepId);
    } else {
        completedIds.delete(stepId);
    }

    const orderedStepIds = Array.isArray(state.lesson?.steps)
        ? state.lesson.steps.map((step) => step.id)
        : [...completedIds];
    const completedStepIds = orderedStepIds.filter((id) => completedIds.has(id));
    const totalCount = Number(state.progress?.total_count) || orderedStepIds.length;

    state.progress = {
        lesson_id: state.lesson?.id,
        completed_step_ids: completedStepIds,
        completed_count: completedStepIds.length,
        total_count: totalCount,
        percent: totalCount
            ? Math.round((completedStepIds.length / totalCount) * 100)
            : 0,
    };
};

const toggleCurrentStepProgress = async () => {
    if (state.currentStepId === null || state.isProgressSaving) {
        return;
    }

    const isCompleted = getCompletedStepIds().has(state.currentStepId);
    state.isProgressSaving = true;
    renderProgressState();

    try {
        const response = await authFetch(
            `/api/progress/steps/${encodeURIComponent(state.currentStepId)}`,
            { method: isCompleted ? 'DELETE' : 'POST' }
        );
        if (!response.ok) {
            throw new Error('progress-request-failed');
        }

        updateLocalProgress(state.currentStepId, !isCompleted);
    } finally {
        state.isProgressSaving = false;
        renderProgressState();
    }
};

const handleDrawerNavigation = (event) => {
    const link = event.target.closest('[data-drawer-step-id]');
    if (!link) {
        return;
    }

    event.preventDefault();
    elements.drawerList
        .querySelectorAll('[aria-current="step"]')
        .forEach((currentLink) => {
            currentLink.removeAttribute('aria-current');
            currentLink.querySelector('.step-drawer__status').textContent = '○';
        });
    link.setAttribute('aria-current', 'step');
    link.querySelector('.step-drawer__status').textContent = '●';
    setDrawerOpen(false);
    window.location.assign(link.href);
};

const localizePage = () => {
    document.title = messages.documentTitle;
    elements.backToLesson.textContent = messages.backToLesson;
    elements.title.textContent = messages.stepTitle;
    elements.progress.textContent = format(
        messages.progress,
        { current: 1, total: 12 }
    );
    elements.placeholder.textContent = messages.contentLoading;
    elements.navigation.setAttribute(
        'aria-label',
        messages.navigationLabel
    );
    elements.previousStep.textContent = messages.previousStep;
    elements.nextStep.textContent = messages.nextStep;
};

const createStatus = (message, { error = false } = {}) => {
    const status = document.createElement('div');
    status.className = 'step-viewer__placeholder';
    status.classList.toggle('step-viewer__placeholder--error', error);
    status.textContent = message;
    return status;
};

const getImageFileIds = (content) => [
    ...new Set(
        getStepBlocks(content)
            .filter((block) => block.type === 'image')
            .map((block) => block.data.file_id)
    ),
];

const loadImageSources = async (content) => {
    const fileIds = getImageFileIds(content);
    if (fileIds.length === 0) {
        return;
    }

    const params = new URLSearchParams();
    fileIds.forEach((fileId) => params.append('ids', String(fileId)));

    const response = await authFetch(`/api/files?${params}`);
    if (!response.ok) {
        return;
    }

    const files = await response.json();
    files.forEach((file) => registerImageSource(file.id, file.url));
};

const loadStep = async () => {
    const stepId = Number(elements.root?.dataset.stepId);
    if (!Number.isInteger(stepId) || stepId <= 0) {
        throw new Error('invalid-step-id');
    }

    const courseSlug = elements.root?.dataset.courseSlug?.trim();
    if (!courseSlug) {
        throw new Error('invalid-course-slug');
    }

    const params = new URLSearchParams({
        course_slug: courseSlug,
    });
    const response = await authFetch(
        `/api/steps/${encodeURIComponent(stepId)}/viewer?${params}`
    );
    if (!response.ok) {
        throw new Error('step-request-failed');
    }

    const viewer = await response.json();
    const { step, navigation, lesson } = viewer;
    state.currentStepId = step.id;
    state.lesson = lesson;
    state.progress = await loadLessonProgress(lesson.id);
    try {
        await loadImageSources(step.content);
    } catch {
        // The remaining blocks can still be displayed without resolved images.
    }

    elements.title.textContent = step.title;
    elements.progress.textContent = format(messages.progress, {
        current: navigation.position,
        total: navigation.total,
    });
    document.title = format(messages.stepDocumentTitle, {
        title: step.title,
    });
    renderStep(elements.content, step.content, {
        renderEmpty: () => createStatus(messages.contentEmpty),
    });
    renderDrawer(lesson, step.id);
    renderProgressState();
};

const init = async () => {
    if (!elements.root) {
        return;
    }

    initDrawer();
    elements.drawerList.addEventListener('click', handleDrawerNavigation);
    elements.completeToggle?.addEventListener('click', toggleCurrentStepProgress);
    localizePage();
    try {
        requireToken();
        await loadStep();
    } catch {
        showDrawerMessage('Не удалось загрузить шаги урока.', { error: true });
        elements.content.replaceChildren(
            createStatus(messages.contentLoadError, { error: true })
        );
    } finally {
        elements.content.setAttribute('aria-busy', 'false');
    }
};

init();
