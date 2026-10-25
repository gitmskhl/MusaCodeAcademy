const normalizeLine = (line) => ({
    type: line?.type === 'input' ? 'input' : 'output',
    text: line?.text ?? '',
});

export const renderConsoleBlock = (block) => {
    const consoleBlock = document.createElement('section');
    consoleBlock.className = 'rendered-console';
    consoleBlock.setAttribute('aria-label', 'Консоль');

    const header = document.createElement('div');
    header.className = 'rendered-console__header';
    header.setAttribute('aria-hidden', 'true');

    const controls = document.createElement('span');
    controls.className = 'rendered-console__controls';
    controls.innerHTML = '<i></i><i></i><i></i>';

    const title = document.createElement('span');
    title.className = 'rendered-console__title';
    title.textContent = 'Консоль';

    header.append(controls, title);

    const body = document.createElement('div');
    body.className = 'rendered-console__body';

    const lines = (
        Array.isArray(block.data?.lines) ? block.data.lines : []
    ).map(normalizeLine);
    if (lines.length === 0) {
        const placeholder = document.createElement('p');
        placeholder.className = 'rendered-console__placeholder';
        placeholder.textContent = 'Пустая консоль';
        body.appendChild(placeholder);
    } else {
        lines.forEach((line) => {
            const row = document.createElement('div');
            row.className = `rendered-console__line rendered-console__line--${line.type}`;

            if (line.type === 'input') {
                const prompt = document.createElement('span');
                prompt.className = 'rendered-console__prompt';
                prompt.textContent = '❯';

                const text = document.createElement('span');
                text.className = 'rendered-console__text';
                text.textContent = line.text;
                row.append(prompt, text);
            } else {
                row.textContent = line.text;
            }

            body.appendChild(row);
        });
    }

    consoleBlock.append(header, body);
    return consoleBlock;
};
