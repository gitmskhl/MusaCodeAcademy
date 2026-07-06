import { getStepBlocks } from './step-renderer/layout-renderers.js';
import { registerImageSource } from './step-renderer/image-sources.js';
import { renderStep } from './step-renderer/step-renderer.js';

const TOKEN_KEY = 'musa_code_academy_token';

const locales = Object.freeze({
    ru: {
        documentTitle: 'Материал урока',
        stepDocumentTitle: '{title} — Материал урока',
        backToLesson: '← К уроку',
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

const renderDrawerSteps = (steps, currentStepId) => {
    elements.drawerList.replaceChildren();
    elements.drawerMessage.hidden = true;
    elements.drawerMessage.classList.remove('step-drawer__message--error');

    if (steps.length === 0) {
        showDrawerMessage('В этом уроке пока нет шагов.');
        return;
    }

    const fragment = document.createDocumentFragment();
    steps.forEach((step) => {
        const isCurrent = step.id === currentStepId;
        const item = document.createElement('li');
        const link = document.createElement('a');
        const status = document.createElement('span');
        const title = document.createElement('span');

        item.className = 'step-drawer__item';
        link.className = 'step-drawer__link';
        link.href = getStepUrl(step.id);
        link.dataset.drawerStepId = String(step.id);
        if (isCurrent) {
            link.setAttribute('aria-current', 'step');
        }

        status.className = 'step-drawer__status';
        status.setAttribute('aria-hidden', 'true');
        status.textContent = isCurrent ? '●' : '○';
        title.textContent = step.title;

        link.append(status, title);
        item.append(link);
        fragment.append(item);
    });
    elements.drawerList.append(fragment);
};

const loadDrawer = async (lessonId, currentStepId) => {
    try {
        const [lessonResponse, stepsResponse] = await Promise.all([
            fetch(`/api/lessons/${encodeURIComponent(lessonId)}`),
            fetch(`/api/lessons/${encodeURIComponent(lessonId)}/steps`),
        ]);
        if (!lessonResponse.ok || !stepsResponse.ok) {
            throw new Error('drawer-request-failed');
        }

        const [lesson, steps] = await Promise.all([
            lessonResponse.json(),
            stepsResponse.json(),
        ]);
        elements.drawerTitle.textContent = lesson.title;
        renderDrawerSteps(Array.isArray(steps) ? steps : [], currentStepId);
    } catch {
        elements.drawerTitle.textContent = 'Урок';
        showDrawerMessage('Не удалось загрузить шаги урока.', { error: true });
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

    const token = localStorage.getItem(TOKEN_KEY);
    const headers = token
        ? { Authorization: `Bearer ${token}` }
        : {};
    const response = await fetch(`/api/files?${params}`, { headers });
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
    const response = await fetch(
        `/api/steps/${encodeURIComponent(stepId)}/viewer?${params}`
    );
    if (!response.ok) {
        throw new Error('step-request-failed');
    }

    const viewer = await response.json();
    const { step, navigation } = viewer;
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
    await loadDrawer(step.lesson_id, step.id);
};

const init = async () => {
    if (!elements.root) {
        return;
    }

    initDrawer();
    elements.drawerList.addEventListener('click', handleDrawerNavigation);
    localizePage();
    try {
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
