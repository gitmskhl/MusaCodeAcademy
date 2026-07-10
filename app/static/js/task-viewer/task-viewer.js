import { createCodeEditorView } from '../step-renderer/codemirror/code-editor-view.js';

const createMetaItem = (icon, label, value) => {
    const item = document.createElement('span');
    item.className = 'task-viewer__meta-item';
    item.textContent = `${icon} ${label}: ${value}`;
    return item;
};

const createDivider = () => {
    const divider = document.createElement('div');
    divider.className = 'task-viewer__divider';
    divider.setAttribute('aria-hidden', 'true');
    return divider;
};

const createSubmitButton = () => {
    const button = document.createElement('button');
    button.className = 'task-viewer__submit';
    button.type = 'button';
    button.textContent = 'Отправить решение';
    return button;
};

export const clearTaskViewer = (container) => {
    container.replaceChildren();
    container.hidden = true;
};

export const renderTaskError = (container, message) => {
    const card = document.createElement('article');
    card.className = 'task-viewer__card task-viewer__card--error';
    card.setAttribute('role', 'alert');
    card.textContent = message;

    container.replaceChildren(card);
    container.hidden = false;
};

export const renderTaskViewer = (container, task) => {
    let sourceCode = task.starter_code || '';

    const card = document.createElement('article');
    card.className = 'task-viewer__card';

    const header = document.createElement('header');
    header.className = 'task-viewer__header';

    const title = document.createElement('h2');
    title.className = 'task-viewer__title';
    title.textContent = 'Практическое задание';

    const meta = document.createElement('div');
    meta.className = 'task-viewer__meta';
    meta.append(
        createMetaItem('⏱', 'Время', `${task.time_limit_ms} мс`),
        createMetaItem('💾', 'Память', `${task.memory_limit_mb} МБ`)
    );

    header.append(title, meta);

    const editorHost = document.createElement('div');
    editorHost.className = 'task-viewer__code-editor';

    const actions = document.createElement('div');
    actions.className = 'task-viewer__actions';

    const submitButton = createSubmitButton();
    submitButton.addEventListener('click', () => {
        console.log('TODO: submit solution', {
            task_id: task.id,
            source_code: sourceCode,
        });
    });

    actions.append(submitButton);
    card.append(header, createDivider(), editorHost, createDivider(), actions);
    container.replaceChildren(card);
    container.hidden = false;

    createCodeEditorView({
        parent: editorHost,
        document: sourceCode,
        language: 'python',
        onChange: (value) => {
            sourceCode = value;
        },
    });
};
