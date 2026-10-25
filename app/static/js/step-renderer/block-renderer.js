import { renderBrowserPythonBlock } from './block-renderers/browser-python-renderer.js';
import { renderCalloutBlock } from './block-renderers/callout-renderer.js';
import { renderCodeBlock } from './block-renderers/code-renderer.js';
import { renderConsoleBlock } from './block-renderers/console-renderer.js';
import { renderImageBlock } from './block-renderers/image-renderer.js';
import { renderTextBlock } from './block-renderers/text-renderer.js';
import { renderVideoBlock } from './block-renderers/video-renderer.js';

const blockRenderers = new Map([
    ['text', renderTextBlock],
    ['image', renderImageBlock],
    ['code', renderCodeBlock],
    ['browser_python', renderBrowserPythonBlock],
    ['console', renderConsoleBlock],
    ['callout', renderCalloutBlock],
    ['video', renderVideoBlock],
]);

const renderUnknownBlock = (block) => {
    const fallback = document.createElement('p');
    fallback.className = 'rendered-block__placeholder';
    fallback.textContent =
        `Отображение блоков «${block.type}» недоступно.`;
    return fallback;
};

export const renderBlock = (block, options = {}) => {
    const renderer = blockRenderers.get(block.type) ?? renderUnknownBlock;
    return renderer(block, options);
};
