const createImagePlaceholder = () => {
    const placeholder = document.createElement('div');
    placeholder.className = 'preview-block__placeholder preview-image__placeholder';
    placeholder.innerHTML = `
        <span aria-hidden="true">▧</span>
        <p>No image selected</p>
    `;
    return placeholder;
};

export const renderImagePreview = (block) => {
    if (!block.data.url) {
        return createImagePlaceholder();
    }

    const figure = document.createElement('figure');
    figure.className = 'preview-image';

    const image = document.createElement('img');
    image.src = block.data.url;
    image.alt = block.data.alt ?? '';
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
