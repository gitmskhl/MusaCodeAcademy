export const renderCodeBlock = (block) => {
    if (!block.data.code) {
        const placeholder = document.createElement('p');
        placeholder.className = 'rendered-block__placeholder';
        placeholder.textContent = 'Click to add code…';
        return placeholder;
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'rendered-code';

    if (block.data.language) {
        const language = document.createElement('span');
        language.className = 'rendered-code__language';
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
