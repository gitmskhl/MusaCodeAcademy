export const renderCodePreview = (block) => {
    if (!block.data.code) {
        const placeholder = document.createElement('div');
        placeholder.className = 'preview-block__placeholder preview-code__placeholder';
        placeholder.textContent = 'Empty code block';
        return placeholder;
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'preview-code';

    if (block.data.language) {
        const language = document.createElement('span');
        language.className = 'preview-code__language';
        language.textContent = block.data.language;
        wrapper.appendChild(language);
    }

    const pre = document.createElement('pre');
    const code = document.createElement('code');
    code.textContent = block.data.code;
    pre.appendChild(code);
    wrapper.appendChild(pre);
    return wrapper;
};
