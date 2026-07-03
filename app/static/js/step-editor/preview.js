import { renderCodePreview } from './preview-renderers/code-renderer.js';
import { renderImagePreview } from './preview-renderers/image-renderer.js';
import { renderTextPreview } from './preview-renderers/text-renderer.js';

const previewRenderers = new Map([
    ['text', renderTextPreview],
    ['image', renderImagePreview],
    ['code', renderCodePreview],
]);

const layoutLabels = {
    vertical: 'Vertical',
    two_columns: 'Two columns',
};

const createEmptyPreview = () => {
    const empty = document.createElement('div');
    empty.className = 'step-preview__empty';
    empty.innerHTML = `
        <span class="step-preview__empty-icon" aria-hidden="true">□</span>
        <strong>This step has no content yet</strong>
        <p>Add a block in Editor mode to see it here.</p>
    `;
    return empty;
};

const renderUnknownBlock = (block) => {
    const fallback = document.createElement('div');
    fallback.className = 'preview-block__placeholder';
    fallback.textContent = `Preview is unavailable for “${block.type}” blocks.`;
    return fallback;
};

const createPreviewBlock = (block, index) => {
    const renderer = previewRenderers.get(block.type) ?? renderUnknownBlock;
    const wrapper = document.createElement('section');
    wrapper.className = `preview-block preview-block--${block.type}`;
    wrapper.dataset.previewBlockIndex = String(index);
    wrapper.appendChild(renderer(block));
    return wrapper;
};

export const registerPreviewRenderer = (type, renderer) => {
    previewRenderers.set(type, renderer);
};

export const renderPreview = (container, step) => {
    const header = document.createElement('header');
    header.className = 'step-preview__header';

    const heading = document.createElement('div');
    const eyebrow = document.createElement('p');
    eyebrow.className = 'step-preview__eyebrow';
    eyebrow.textContent = 'Learner view';
    const title = document.createElement('h2');
    title.textContent = 'Step preview';
    heading.append(eyebrow, title);

    const layoutBadge = document.createElement('span');
    layoutBadge.className = 'step-preview__layout';
    layoutBadge.textContent = layoutLabels[step.layout] ?? step.layout;
    header.append(heading, layoutBadge);

    const content = document.createElement('div');
    content.className = `step-preview__content step-preview__content--${step.layout}`;

    if (step.content.blocks.length === 0) {
        content.appendChild(createEmptyPreview());
    } else {
        const fragment = document.createDocumentFragment();
        step.content.blocks.forEach((block, index) => {
            fragment.appendChild(createPreviewBlock(block, index));
        });
        content.appendChild(fragment);
    }

    container.replaceChildren(header, content);
};
