const getVerticalBlocks = (content) => content.blocks ?? [];

const getTwoColumnBlocks = (content) => {
    const blocks = [];
    const left = content.left ?? [];
    const right = content.right ?? [];
    const rowCount = Math.max(left.length, right.length);

    for (let row = 0; row < rowCount; row += 1) {
        if (left[row]) {
            blocks.push(left[row]);
        }
        if (right[row]) {
            blocks.push(right[row]);
        }
    }
    return blocks;
};

export const getStepBlocks = (content) => {
    if (content.layout === 'two_columns') {
        return getTwoColumnBlocks(content);
    }
    return getVerticalBlocks(content);
};

export const renderStepLayout = (container, content, renderItem) => {
    container.classList.toggle(
        'step-renderer--two-columns',
        content.layout === 'two_columns'
    );

    const fragment = document.createDocumentFragment();
    getStepBlocks(content).forEach((block, index) => {
        fragment.appendChild(renderItem(block, index));
    });
    container.appendChild(fragment);
};
