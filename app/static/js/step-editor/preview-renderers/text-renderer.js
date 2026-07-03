export const renderTextPreview = (block) => {
    const text = document.createElement('div');
    text.className = 'preview-text';

    if (block.data.text) {
        text.textContent = block.data.text;
    } else {
        text.classList.add('preview-block__placeholder');
        text.textContent = 'Empty text block';
    }

    return text;
};
