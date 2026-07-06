import { renderBlock } from './block-renderer.js';
import { getStepBlocks, renderStepLayout } from './layout-renderers.js';

const renderBlockContent = (block, index) =>
    renderBlock(block, { index });

export const renderStep = (
    container,
    content,
    {
        renderItem = renderBlockContent,
        renderEmpty = null,
    } = {}
) => {
    container.replaceChildren();
    container.classList.add('step-renderer');

    if (getStepBlocks(content).length === 0) {
        container.classList.remove('step-renderer--two-columns');
        if (renderEmpty) {
            container.appendChild(renderEmpty());
        }
        return;
    }

    renderStepLayout(container, content, renderItem);
};
