export const step = {
    version: 1,
    layout: 'vertical',
    content: {
        blocks: [],
    },
};

const listeners = new Set();

const notify = (change) => {
    listeners.forEach((listener) => listener(step, change));
};

export const subscribeToStep = (listener) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
};

export const setLayout = (layout) => {
    step.layout = layout;
    notify({ type: 'layout-changed' });
};

export const addBlock = (block) => {
    step.content.blocks.push(block);
    const index = step.content.blocks.length - 1;
    notify({ type: 'block-added', index });
    return index;
};

export const removeBlock = (index) => {
    if (!step.content.blocks[index]) {
        return false;
    }

    step.content.blocks.splice(index, 1);
    notify({ type: 'block-removed', index });
    return true;
};

export const updateBlockData = (index, values) => {
    const block = step.content.blocks[index];

    if (!block) {
        return false;
    }

    Object.assign(block.data, values);
    notify({ type: 'block-data-updated', index });
    return true;
};
