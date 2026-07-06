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

    const response = await fetch(
        `/api/steps/${encodeURIComponent(stepId)}`
    );
    if (!response.ok) {
        throw new Error('step-request-failed');
    }

    const step = await response.json();
    try {
        await loadImageSources(step.content);
    } catch {
        // The remaining blocks can still be displayed without resolved images.
    }

    elements.title.textContent = step.title;
    document.title = format(messages.stepDocumentTitle, {
        title: step.title,
    });
    renderStep(elements.content, step.content, {
        renderEmpty: () => createStatus(messages.contentEmpty),
    });
};

const init = async () => {
    if (!elements.root) {
        return;
    }

    localizePage();
    try {
        await loadStep();
    } catch {
        elements.content.replaceChildren(
            createStatus(messages.contentLoadError, { error: true })
        );
    } finally {
        elements.content.setAttribute('aria-busy', 'false');
    }
};

init();
