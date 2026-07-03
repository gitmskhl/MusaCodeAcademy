export const renderTextEditor = ({ block, index, onChange }) => {
    const editor = document.createElement('div');
    editor.className = 'block-properties';

    const label = document.createElement('label');
    label.className = 'property-field__label';
    label.htmlFor = `text-block-${index}`;
    label.textContent = 'Text';

    const textarea = document.createElement('textarea');
    textarea.className = 'property-field__textarea';
    textarea.id = label.htmlFor;
    textarea.rows = 14;
    textarea.placeholder = 'Write the content for this block…';
    textarea.value = block.data.text ?? '';
    textarea.dataset.propertiesFirstField = '';
    textarea.addEventListener('input', () => {
        onChange({ text: textarea.value });
    });

    editor.append(label, textarea);
    return editor;
};
