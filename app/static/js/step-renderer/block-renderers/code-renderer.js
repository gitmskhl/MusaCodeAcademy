import { mountCodeEditor } from '../codemirror/code-editor-instance.js';

export const renderCodeBlock = (
    block,
    { index, onChange = () => {} } = {}
) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'rendered-code';

    if (block.data.language) {
        const language = document.createElement('span');
        language.className = 'rendered-code__language';
        language.textContent = block.data.language;
        wrapper.appendChild(language);
    }

    mountCodeEditor({
        block,
        index,
        parent: wrapper,
        editable: false,
        onChange: (value) => onChange({ code: value }),
    });
    return wrapper;
};
