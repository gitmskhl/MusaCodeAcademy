import { getImageSource } from '../image-sources.js';

const clampWidth = (value) => {
    const width = Number(value);
    return Number.isFinite(width) ? Math.min(100, Math.max(10, width)) : 100;
};

const createPlaceholder = () => {
    const placeholder = document.createElement('div');
    placeholder.className = 'rendered-block__placeholder rendered-image__placeholder';
    placeholder.innerHTML = `
        <span aria-hidden="true">▧</span>
        <p>No image uploaded</p>
    `;
    return placeholder;
};

export const renderImageBlock = (block) => {
    const figure = document.createElement('figure');
    figure.className = 'rendered-image';
    figure.style.width = `${clampWidth(block.data.width)}%`;

    const source = getImageSource(block.data.file_id);
    if (!source) {
        figure.appendChild(createPlaceholder());
        return figure;
    }

    const image = document.createElement('img');
    image.src = source;
    image.alt = block.data.caption ?? '';
    figure.appendChild(image);

    if (block.data.caption) {
        const caption = document.createElement('figcaption');
        caption.textContent = block.data.caption;
        figure.appendChild(caption);
    }

    image.addEventListener('error', () => {
        figure.replaceChildren(createPlaceholder());
    });
    return figure;
};
