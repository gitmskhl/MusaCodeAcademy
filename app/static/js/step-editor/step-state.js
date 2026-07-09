import { getStepBlocks } from '../step-renderer/layout-renderers.js';

export const step = {
    content: {
        version: 1,
        layout: 'vertical',
        blocks: [],
    },
};

const listeners = new Set();

const notify = (change) => {
    listeners.forEach((listener) => listener(step, change));
};

const normalizeBlock = (block) => {
    if (block?.type !== 'callout') {
        return block;
    }

    return {
        ...block,
        data: {
            variant: block.data?.variant ?? 'info',
            title: block.data?.title ?? '',
            content: block.data?.content ?? '',
        },
    };
};

const normalizeContent = (content) => {
    const normalized = structuredClone(content);

    if (normalized.layout === 'two_columns') {
        normalized.left = (normalized.left ?? []).map(normalizeBlock);
        normalized.right = (normalized.right ?? []).map(normalizeBlock);
        return normalized;
    }

    normalized.blocks = (normalized.blocks ?? []).map(normalizeBlock);
    return normalized;
};

export const getBlocks = () => {
    return getStepBlocks(step.content);
};

const setBlocks = (blocks) => {
    if (step.content.layout === 'vertical') {
        step.content.blocks = blocks;
        return;
    }

    step.content.left = blocks.filter((_block, index) => index % 2 === 0);
    step.content.right = blocks.filter((_block, index) => index % 2 === 1);
};

export const subscribeToStep = (listener) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
};

export const loadStepContent = (content) => {
    step.content = normalizeContent(content);
    notify({ type: 'step-loaded' });
};

export const setLayout = (layout) => {
    if (layout === step.content.layout) {
        return;
    }

    const blocks = getBlocks();
    if (layout === 'vertical') {
        step.content = {
            version: 1,
            layout: 'vertical',
            blocks,
        };
    } else if (layout === 'two_columns') {
        step.content = {
            version: 1,
            layout: 'two_columns',
            left: blocks.filter((_block, index) => index % 2 === 0),
            right: blocks.filter((_block, index) => index % 2 === 1),
        };
    } else {
        return;
    }
    notify({ type: 'layout-changed' });
};

export const addBlock = (block) => {
    const blocks = getBlocks();
    blocks.push(block);
    setBlocks(blocks);
    const index = blocks.length - 1;
    notify({ type: 'block-added', index });
    return index;
};

export const removeBlock = (index) => {
    const blocks = getBlocks();
    if (!blocks[index]) {
        return false;
    }

    blocks.splice(index, 1);
    setBlocks(blocks);
    notify({ type: 'block-removed', index });
    return true;
};

export const moveBlock = (fromIndex, toIndex) => {
    const blocks = getBlocks();
    if (
        !blocks[fromIndex] ||
        toIndex < 0 ||
        toIndex >= blocks.length ||
        fromIndex === toIndex
    ) {
        return false;
    }

    const [block] = blocks.splice(fromIndex, 1);
    blocks.splice(toIndex, 0, block);
    setBlocks(blocks);
    notify({ type: 'block-moved', fromIndex, toIndex });
    return true;
};

export const updateBlockData = (index, values) => {
    const block = getBlocks()[index];

    if (!block) {
        return false;
    }

    Object.assign(block.data, values);
    notify({ type: 'block-data-updated', index });
    return true;
};
