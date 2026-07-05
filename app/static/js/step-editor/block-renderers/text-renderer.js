import { renderMarkdown } from './markdown.js';

export const renderTextBlock = (block) => {
    if (block.data.text?.trim()) {
        return renderMarkdown(block.data.text);
    }

    const placeholder = document.createElement('p');
    placeholder.className = 'rendered-block__placeholder';
    placeholder.textContent = 'Click to write…';
    return placeholder;
};
