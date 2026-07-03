export const renderPreviewPlaceholder = (container) => {
    const placeholder = document.createElement('div');
    placeholder.className = 'preview-placeholder';
    placeholder.textContent = 'Preview is not implemented yet.';
    container.replaceChildren(placeholder);
};
