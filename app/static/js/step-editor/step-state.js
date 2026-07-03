export const step = {
    version: 1,
    layout: 'vertical',
    content: {
        blocks: [],
    },
};

const listeners = new Set();

const notify = () => {
    listeners.forEach((listener) => listener(step));
};

export const subscribeToStep = (listener) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
};

export const setLayout = (layout) => {
    step.layout = layout;
    notify();
};

export const addBlock = (block) => {
    step.content.blocks.push(block);
    notify();
};
