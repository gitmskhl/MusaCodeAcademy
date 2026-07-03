const blockTypes = new Map([
    [
        'text',
        {
            label: 'Text',
            description: 'Paragraphs and headings',
            icon: 'T',
            createData: () => ({ text: '' }),
        },
    ],
    [
        'image',
        {
            label: 'Image',
            description: 'Image with accessible text',
            icon: '▧',
            createData: () => ({ url: '', alt: '', caption: '' }),
        },
    ],
    [
        'code',
        {
            label: 'Code',
            description: 'Formatted code snippet',
            icon: '</>',
            createData: () => ({ code: '', language: '' }),
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
