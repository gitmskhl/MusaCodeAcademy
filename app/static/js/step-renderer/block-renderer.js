import { renderCalloutBlock } from './block-renderers/callout-renderer.js';
import { renderCodeBlock } from './block-renderers/code-renderer.js';
import { renderImageBlock } from './block-renderers/image-renderer.js';
import { renderTextBlock } from './block-renderers/text-renderer.js';

const blockRenderers = new Map([
    ['text', renderTextBlock],
    ['image', renderImageBlock],
    ['code', renderCodeBlock],
    ['callout', renderCalloutBlock],
]);

const renderUnknownBlock = (block) => {
    const fallback = document.createElement('p');
    fallback.className = 'rendered-block__placeholder';
    fallback.textContent =
        `Rendering is unavailable for “${block.type}” blocks.`;
    return fallback;
};

export const renderBlock = (block, options = {}) => {
    const renderer = blockRenderers.get(block.type) ?? renderUnknownBlock;
    return renderer(block, options);
};
