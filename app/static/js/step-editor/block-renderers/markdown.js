import { marked } from '../../../vendor/marked.esm.js';

export const renderMarkdown = (source) => {
    const container = document.createElement('div');
    container.className = 'rendered-text';
    container.innerHTML = marked.parse(String(source ?? ''), {
        gfm: true,
    });
    return container;
};
