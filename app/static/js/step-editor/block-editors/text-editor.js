const resizeTextarea = (textarea) => {
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.max(80, textarea.scrollHeight)}px`;
};

export const renderTextEditor = ({ block, index, onChange }) => {
    const editor = document.createElement('div');
    editor.className = 'inline-text-editor';

    const textarea = document.createElement('textarea');
    textarea.className = 'inline-text-editor__input';
    textarea.id = `text-block-${index}`;
    textarea.rows = 1;
    textarea.placeholder = 'Write with Markdown…';
    textarea.value = block.data.text ?? '';
    textarea.dataset.propertiesFirstField = '';
    textarea.setAttribute('aria-label', 'Markdown text');
    textarea.addEventListener('input', () => {
        resizeTextarea(textarea);
        onChange({ text: textarea.value });
    });

    editor.appendChild(textarea);
    requestAnimationFrame(() => resizeTextarea(textarea));
    return editor;
};
