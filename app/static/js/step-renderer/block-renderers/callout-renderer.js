import { renderMarkdown } from './markdown.js';

const calloutVariants = {
    info: {
        label: 'Info',
        icon: 'ℹ️',
    },
    tip: {
        label: 'Tip',
        icon: '💡',
    },
    important: {
        label: 'Important',
        icon: '⭐',
    },
    warning: {
        label: 'Warning',
        icon: '⚠️',
    },
    error: {
        label: 'Error',
        icon: '❌',
    },
};

const normalizeVariant = (variant) =>
    Object.hasOwn(calloutVariants, variant) ? variant : 'info';

export const renderCalloutBlock = (block) => {
    const variant = normalizeVariant(block.data.variant);
    const definition = calloutVariants[variant];
    const callout = document.createElement('aside');
    callout.className = `rendered-callout rendered-callout--${variant}`;
    callout.setAttribute('aria-label', `${definition.label} callout`);

    const icon = document.createElement('span');
    icon.className = 'rendered-callout__icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = definition.icon;

    const body = document.createElement('div');
    body.className = 'rendered-callout__body';

    if (block.data.title?.trim()) {
        const title = document.createElement('p');
        title.className = 'rendered-callout__title';
        title.textContent = block.data.title.trim();
        body.appendChild(title);
    }

    if (block.data.content?.trim()) {
        body.appendChild(renderMarkdown(block.data.content));
    } else {
        const placeholder = document.createElement('p');
        placeholder.className = 'rendered-block__placeholder';
        placeholder.textContent = 'Click to write a callout...';
        body.appendChild(placeholder);
    }

    callout.append(icon, body);
    return callout;
};
