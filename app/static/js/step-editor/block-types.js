const blockTypes = new Map([
    [
        'text',
        {
            label: 'Text',
            description: 'Paragraphs and headings',
            icon: 'T',
            createData: () => ({ text: '' }),
            summarize: (data) => {
                const firstLine = data.text?.split(/\r?\n/, 1)[0].trim();
                return firstLine || 'Empty text block';
            },
        },
    ],
    [
        'image',
        {
            label: 'Image',
            description: 'Uploaded image with caption',
            icon: '▧',
            createData: () => ({ file_id: null, width: 100, caption: '' }),
            summarize: (data) =>
                data.caption?.trim() ||
                (data.file_id != null ? 'Uploaded image' : 'No image selected'),
        },
    ],
    [
        'code',
        {
            label: 'Code',
            description: 'Formatted code snippet',
            icon: '</>',
            createData: () => ({ code: '', language: '' }),
            summarize: (data) => {
                const firstLine = data.code?.split(/\r?\n/, 1)[0].trim();
                return firstLine || 'Empty code block';
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
        throw new Error(`Unsupported block type: ${type}`);
    }

    return {
        type,
        data: definition.createData(),
    };
};
