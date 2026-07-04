import { mountCodeEditor } from '../codemirror/code-editor-instance.js';

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

    const codeField = document.createElement('div');
    codeField.className = 'property-field';

    const codeText = document.createElement('span');
    codeText.className = 'property-field__label';
    codeText.textContent = 'Code';

    codeField.appendChild(codeText);
    const codeEditor = mountCodeEditor({
        block,
        index,
        parent: codeField,
        editable: true,
        onChange: (value) => onChange({ code: value }),
    });

    language.addEventListener('input', () => {
        onChange({ language: language.value });
        codeEditor.controller.setLanguage(language.value);
    });

    editor.append(languageLabel, codeField);
    return editor;
};
