import { createCodeEditorView } from '../codemirror/code-editor-view.js';

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

    const code = document.createElement('div');
    code.className = 'code-editor';
    code.id = `code-block-${index}`;
    code.dataset.propertiesFirstField = '';
    code.tabIndex = -1;
    codeField.append(codeText, code);

    const codeEditor = createCodeEditorView({
        parent: code,
        document: block.data.code ?? '',
        language: block.data.language ?? '',
        onChange: (value) => onChange({ code: value }),
    });
    code.addEventListener('focus', () => codeEditor.focus());

    language.addEventListener('input', () => {
        onChange({ language: language.value });
        codeEditor.setLanguage(language.value);
    });

    editor.append(languageLabel, codeField);
    return editor;
};
