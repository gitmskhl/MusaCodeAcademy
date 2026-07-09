const resizeTextarea = (textarea) => {
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.max(80, textarea.scrollHeight)}px`;
};

export const createMarkdownTextarea = ({
    id,
    value,
    placeholder = 'Write with Markdown...',
    ariaLabel = 'Markdown text',
    onChange,
}) => {
    const textarea = document.createElement('textarea');
    textarea.className = 'inline-text-editor__input';
    textarea.id = id;
    textarea.rows = 1;
    textarea.placeholder = placeholder;
    textarea.value = value ?? '';
    textarea.dataset.propertiesFirstField = '';
    textarea.setAttribute('aria-label', ariaLabel);
    textarea.addEventListener('input', () => {
        resizeTextarea(textarea);
        onChange(textarea.value);
    });
    requestAnimationFrame(() => resizeTextarea(textarea));
    return textarea;
};

export const renderTextEditor = ({ block, index, onChange }) => {
    const editor = document.createElement('div');
    editor.className = 'inline-text-editor';

    const textarea = createMarkdownTextarea({
        id: `text-block-${index}`,
        value: block.data.text,
        onChange: (value) => onChange({ text: value }),
    });

    editor.appendChild(textarea);
    return editor;
};
