export const renderCodeEditor = ({ block, index, onChange }) => {
    const editor = document.createElement('div');
    editor.className = 'block-properties block-properties--code';

    const languageLabel = document.createElement('label');
    languageLabel.className = 'property-field';
    languageLabel.htmlFor = `code-language-${index}`;

    const languageText = document.createElement('span');
    languageText.className = 'property-field__label';
    languageText.textContent = 'Language';

    const language = document.createElement('input');
    language.className = 'property-field__input property-field__input--language';
    language.id = languageLabel.htmlFor;
    language.type = 'text';
    language.placeholder = 'e.g. Python';
    language.value = block.data.language ?? '';
    languageLabel.append(languageText, language);

    const codeLabel = document.createElement('label');
    codeLabel.className = 'property-field';
    codeLabel.htmlFor = `code-block-${index}`;

    const codeText = document.createElement('span');
    codeText.className = 'property-field__label';
    codeText.textContent = 'Code';

    const code = document.createElement('textarea');
    code.className = 'property-field__textarea property-field__textarea--code';
    code.id = codeLabel.htmlFor;
    code.rows = 10;
    code.placeholder = 'Write or paste code…';
    code.value = block.data.code ?? '';
    code.dataset.propertiesFirstField = '';
    codeLabel.append(codeText, code);

    language.addEventListener('input', () => {
        onChange({ language: language.value });
    });
    code.addEventListener('input', () => onChange({ code: code.value }));

    editor.append(languageLabel, codeLabel);
    return editor;
};
