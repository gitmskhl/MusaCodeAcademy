const blockTypes = new Map([
    [
        'text',
        {
            label: 'Текст',
            description: 'Абзацы и заголовки',
            icon: 'T',
            createData: () => ({ text: '' }),
            summarize: (data) => {
                const firstLine = data.text?.split(/\r?\n/, 1)[0].trim();
                return firstLine || 'Пустой текстовый блок';
            },
        },
    ],
    [
        'image',
        {
            label: 'Изображение',
            description: 'Загруженное изображение с подписью',
            icon: '▧',
            createData: () => ({ file_id: null, width: 100, caption: '' }),
            summarize: (data) =>
                data.caption?.trim() ||
                (data.file_id != null ? 'Загруженное изображение' : 'Изображение не выбрано'),
        },
    ],
    [
        'code',
        {
            label: 'Код',
            description: 'Форматированный фрагмент кода',
            icon: '</>',
            createData: () => ({ code: '', language: '' }),
            summarize: (data) => {
                const firstLine = data.code?.split(/\r?\n/, 1)[0].trim();
                return firstLine || 'Пустой блок кода';
            },
        },
    ],
    [
        'browser_python',
        {
            label: 'Python в браузере',
            description: 'Python-код с запуском на клиенте',
            icon: 'Py',
            createData: () => ({
                code: 'value = input("Введите значение: ")\nprint(f"Вы ввели: {value}")',
                stdin: 'пример',
            }),
            summarize: (data) => {
                const firstLine = data.code?.split(/\r?\n/, 1)[0].trim();
                return firstLine || 'Пустой Python-блок';
            },
        },
    ],
    [
        'console',
        {
            label: 'Консоль',
            description: 'Пример ввода и вывода программы',
            icon: '❯',
            createData: () => ({
                lines: [
                    { type: 'output', text: 'Введите 1-е число' },
                    { type: 'input', text: '65' },
                ],
            }),
            summarize: (data) => {
                const firstLine = data.lines
                    ?.find((line) => line.text?.trim())
                    ?.text.trim();
                const lineCount = data.lines?.length ?? 0;
                return firstLine || `${lineCount} строк в консоли`;
            },
        },
    ],
    [
        'video',
        {
            label: 'Видео',
            description: 'Встраивание Kinescope',
            icon: 'play',
            createData: () => ({
                provider: 'kinescope',
                embed_url: '',
                title: '',
                caption: '',
                aspect_ratio: '16:9',
            }),
            summarize: (data) =>
                data.title?.trim() ||
                data.caption?.trim() ||
                (data.embed_url?.trim()
                    ? 'Видео Kinescope'
                    : 'Видео не добавлено'),
        },
    ],
    [
        'callout',
        {
            label: 'Заметка',
            description: 'Выделенная Markdown-заметка',
            icon: '!',
            createData: () => ({
                variant: 'info',
                title: '',
                content: '',
            }),
            summarize: (data) => {
                const title = data.title?.trim();
                const firstLine = data.content?.split(/\r?\n/, 1)[0].trim();
                return title || firstLine || 'Пустая заметка';
            },
        },
    ],
]);

export const getBlockTypes = () =>
    [...blockTypes.entries()].map(([type, definition]) => ({
        type,
        ...definition,
    }));

export const getBlockType = (type) => blockTypes.get(type);

export const createBlock = (type) => {
    const definition = getBlockType(type);

    if (!definition) {
        throw new Error(`Неподдерживаемый тип блока: ${type}`);
    }

    return {
        type,
        data: definition.createData(),
    };
};
