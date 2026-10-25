const lineTypeOptions = [
    { value: 'output', label: 'Вывод программы' },
    { value: 'input', label: 'Ввод пользователя' },
];

const normalizeLine = (line) => ({
    type: line?.type === 'input' ? 'input' : 'output',
    text: line?.text ?? '',
});

export const renderConsoleEditor = ({ block, onChange }) => {
    const editor = document.createElement('div');
    editor.className = 'inline-console-editor';

    const title = document.createElement('p');
    title.className = 'inline-console-editor__title';
    title.textContent = 'Консоль';

    const rows = document.createElement('div');
    rows.className = 'inline-console-editor__rows';

    const addButton = document.createElement('button');
    addButton.className = 'inline-console-editor__add';
    addButton.type = 'button';
    addButton.textContent = '+ Добавить строку';

    let lines = (
        Array.isArray(block.data?.lines) ? block.data.lines : []
    ).map(normalizeLine);

    const syncLines = () => {
        onChange({ lines: lines.map(normalizeLine) });
    };

    const renderRows = ({ focusIndex = null } = {}) => {
        rows.replaceChildren();

        if (lines.length === 0) {
            const empty = document.createElement('p');
            empty.className = 'inline-console-editor__empty';
            empty.textContent = 'Добавьте строки вывода и ввода.';
            rows.appendChild(empty);
            return;
        }

        lines.forEach((line, lineIndex) => {
            const row = document.createElement('div');
            row.className = 'inline-console-editor__row';

            const select = document.createElement('select');
            select.className = 'inline-console-editor__select';
            select.setAttribute(
                'aria-label',
                `Тип строки консоли ${lineIndex + 1}`
            );
            if (lineIndex === 0) {
                select.dataset.propertiesFirstField = '';
            }

            lineTypeOptions.forEach((option) => {
                const item = document.createElement('option');
                item.value = option.value;
                item.textContent = option.label;
                item.selected = option.value === line.type;
                select.appendChild(item);
            });

            const textInput = document.createElement('input');
            textInput.className = 'inline-console-editor__input';
            textInput.type = 'text';
            textInput.value = line.text;
            textInput.placeholder =
                line.type === 'input' ? '65' : 'Введите 1-е число';
            textInput.setAttribute(
                'aria-label',
                `Текст строки консоли ${lineIndex + 1}`
            );

            const moveUpButton = document.createElement('button');
            moveUpButton.className = 'inline-console-editor__icon-button';
            moveUpButton.type = 'button';
            moveUpButton.textContent = '↑';
            moveUpButton.title = 'Переместить выше';
            moveUpButton.setAttribute(
                'aria-label',
                `Переместить строку ${lineIndex + 1} выше`
            );
            moveUpButton.disabled = lineIndex === 0;

            const moveDownButton = document.createElement('button');
            moveDownButton.className = 'inline-console-editor__icon-button';
            moveDownButton.type = 'button';
            moveDownButton.textContent = '↓';
            moveDownButton.title = 'Переместить ниже';
            moveDownButton.setAttribute(
                'aria-label',
                `Переместить строку ${lineIndex + 1} ниже`
            );
            moveDownButton.disabled = lineIndex === lines.length - 1;

            const deleteButton = document.createElement('button');
            deleteButton.className =
                'inline-console-editor__icon-button inline-console-editor__delete';
            deleteButton.type = 'button';
            deleteButton.textContent = '×';
            deleteButton.title = 'Удалить строку';
            deleteButton.setAttribute(
                'aria-label',
                `Удалить строку консоли ${lineIndex + 1}`
            );

            select.addEventListener('change', () => {
                lines[lineIndex] = {
                    ...lines[lineIndex],
                    type: select.value === 'input' ? 'input' : 'output',
                };
                textInput.placeholder =
                    select.value === 'input' ? '65' : 'Введите 1-е число';
                syncLines();
            });

            textInput.addEventListener('input', () => {
                lines[lineIndex] = {
                    ...lines[lineIndex],
                    text: textInput.value,
                };
                syncLines();
            });

            moveUpButton.addEventListener('click', () => {
                if (lineIndex === 0) {
                    return;
                }
                [lines[lineIndex - 1], lines[lineIndex]] = [
                    lines[lineIndex],
                    lines[lineIndex - 1],
                ];
                syncLines();
                renderRows({ focusIndex: lineIndex - 1 });
            });

            moveDownButton.addEventListener('click', () => {
                if (lineIndex >= lines.length - 1) {
                    return;
                }
                [lines[lineIndex], lines[lineIndex + 1]] = [
                    lines[lineIndex + 1],
                    lines[lineIndex],
                ];
                syncLines();
                renderRows({ focusIndex: lineIndex + 1 });
            });

            deleteButton.addEventListener('click', () => {
                lines = lines.filter((_item, itemIndex) => itemIndex !== lineIndex);
                syncLines();
                renderRows({ focusIndex: Math.min(lineIndex, lines.length - 1) });
            });

            row.append(
                select,
                textInput,
                moveUpButton,
                moveDownButton,
                deleteButton
            );
            rows.appendChild(row);
        });

        if (focusIndex !== null) {
            rows
                .querySelectorAll('.inline-console-editor__input')
                .item(focusIndex)
                ?.focus();
        }
    };

    addButton.addEventListener('click', () => {
        lines = [...lines, { type: 'output', text: '' }];
        syncLines();
        renderRows({ focusIndex: lines.length - 1 });
    });

    renderRows();
    editor.append(title, rows, addButton);
    return editor;
};
