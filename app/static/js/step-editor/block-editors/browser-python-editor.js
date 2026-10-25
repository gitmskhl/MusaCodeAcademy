import {
    mountCodeEditor,
} from '../../step-renderer/codemirror/code-editor-instance.js';

export const renderBrowserPythonEditor = ({ block, index, onChange }) => {
    const editor = document.createElement('div');
    editor.className = 'block-properties block-properties--browser-code';

    const codeField = document.createElement('div');
    codeField.className = 'property-field';

    const codeText = document.createElement('span');
    codeText.className = 'property-field__label';
    codeText.textContent = 'Python';

    codeField.appendChild(codeText);
    mountCodeEditor({
        block,
        index,
        language: 'python',
        parent: codeField,
        editable: true,
        onChange: (value) => onChange({ code: value }),
    });

    const stdinLabel = document.createElement('label');
    stdinLabel.className = 'property-field';
    stdinLabel.htmlFor = `browser-python-stdin-${index}`;

    const stdinText = document.createElement('span');
    stdinText.className = 'property-field__label';
    stdinText.textContent = 'Входные данные по умолчанию';

    const stdin = document.createElement('textarea');
    stdin.className =
        'property-field__textarea property-field__textarea--stdin';
    stdin.id = stdinLabel.htmlFor;
    stdin.spellcheck = false;
    stdin.rows = 4;
    stdin.placeholder = 'Каждая строка будет прочитана отдельным input()';
    stdin.value = block.data.stdin ?? '';
    stdin.addEventListener('input', () => {
        onChange({ stdin: stdin.value });
    });

    stdinLabel.append(stdinText, stdin);
    editor.append(codeField, stdinLabel);
    return editor;
};
