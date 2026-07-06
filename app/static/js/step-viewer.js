const locales = Object.freeze({
    ru: {
        documentTitle: 'Материал урока',
        backToLesson: '← К уроку',
        stepTitle: 'Название шага',
        progress: '{current} / {total}',
        contentPlaceholder: 'Материал шага появится здесь.',
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
        (result, [key, value]) => result.replace(`{${key}}`, value),
        template
    );

const localizePage = () => {
    const messages = getLocale();

    document.title = messages.documentTitle;
    document.querySelector('[data-back-to-lesson]').textContent =
        messages.backToLesson;
    document.querySelector('[data-step-title]').textContent =
        messages.stepTitle;
    document.querySelector('[data-step-progress]').textContent = format(
        messages.progress,
        { current: 1, total: 12 }
    );
    document.querySelector('[data-content-placeholder]').textContent =
        messages.contentPlaceholder;
    document.querySelector('[data-step-navigation]').setAttribute(
        'aria-label',
        messages.navigationLabel
    );
    document.querySelector('[data-previous-step]').textContent =
        messages.previousStep;
    document.querySelector('[data-next-step]').textContent =
        messages.nextStep;
};

localizePage();
