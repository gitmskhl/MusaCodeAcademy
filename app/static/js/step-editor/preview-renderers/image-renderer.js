import { getImageSource } from '../image-sources.js';

const createImagePlaceholder = () => {
    const placeholder = document.createElement('div');
    placeholder.className = 'preview-block__placeholder preview-image__placeholder';
    placeholder.innerHTML = `
        <span aria-hidden="true">▧</span>
        <p>No image uploaded</p>
    `;
    return placeholder;
};

const clampWidth = (value) => {
    const width = Number(value);
    return Number.isFinite(width) ? Math.min(100, Math.max(10, width)) : 100;
};

export const renderImagePreview = (block) => {
    const source = getImageSource(block.data.file_id);
    if (!source) {
        return createImagePlaceholder();
    }

    const figure = document.createElement('figure');
    figure.className = 'preview-image';
    figure.style.width = `${clampWidth(block.data.width)}%`;

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
        figure.replaceChildren(createImagePlaceholder());
    });

    return figure;
};
