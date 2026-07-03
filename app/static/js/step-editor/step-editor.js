import { createBlock, getBlockTypes } from './block-types.js';
import { renderBlockList } from './block-list-renderer.js';
import { renderPreview } from './preview.js';
import { renderPropertiesPanel } from './properties-panel.js';
import {
    addBlock,
    removeBlock,
    setLayout,
    step,
    subscribeToStep,
    updateBlockData,
} from './step-state.js';

const elements = {
    root: document.querySelector('[data-step-editor]'),
    backButton: document.querySelector('[data-back-button]'),
    editorPanel: document.querySelector('[data-editor-panel]'),
    previewPanel: document.querySelector('[data-preview-panel]'),
    propertiesPanel: document.querySelector('[data-properties-panel]'),
    modeButtons: [...document.querySelectorAll('[data-mode]')],
    layoutOptions: [...document.querySelectorAll('[data-layout-option]')],
    blockList: document.querySelector('[data-block-list]'),
    addBlockButton: document.querySelector('[data-add-block-button]'),
    blockMenu: document.querySelector('[data-block-menu]'),
};

let selectedBlockIndex = null;
let focusPropertiesAfterRender = false;

const renderLayout = () => {
    elements.layoutOptions.forEach((option) => {
        option.checked = option.value === step.layout;
    });
};

const renderBlocks = () => {
    renderBlockList(elements.blockList, step.content.blocks, selectedBlockIndex);
};

const renderProperties = () => {
    const block =
        selectedBlockIndex === null
            ? null
            : step.content.blocks[selectedBlockIndex] ?? null;

    renderPropertiesPanel(elements.propertiesPanel, {
        block,
        index: selectedBlockIndex,
        focusFirstField: focusPropertiesAfterRender,
        onChange: (values) => updateBlockData(selectedBlockIndex, values),
    });
    focusPropertiesAfterRender = false;
};

const renderEditor = (currentStep = step, change = { type: 'initial-render' }) => {
    renderLayout();
    renderBlocks();
    renderPreview(elements.previewPanel, currentStep);

    // The active editor already contains the latest typed value. Keeping it
    // mounted preserves textarea focus and cursor position during live updates.
    if (change.type !== 'block-data-updated') {
        renderProperties();
    }
};

const renderBlockMenu = () => {
    const fragment = document.createDocumentFragment();

    getBlockTypes().forEach((definition) => {
        const button = document.createElement('button');
        button.className = 'block-menu__item';
        button.type = 'button';
        button.role = 'menuitem';
        button.dataset.blockType = definition.type;
        button.innerHTML = `
            <span class="block-menu__icon" aria-hidden="true"></span>
            <span>
                <span class="block-menu__label"></span>
                <span class="block-menu__description"></span>
            </span>
        `;
        button.querySelector('.block-menu__icon').textContent = definition.icon;
        button.querySelector('.block-menu__label').textContent = definition.label;
        button.querySelector('.block-menu__description').textContent =
            definition.description;
        fragment.appendChild(button);
    });

    elements.blockMenu.replaceChildren(fragment);
};

const closeBlockMenu = ({ returnFocus = false } = {}) => {
    elements.blockMenu.hidden = true;
    elements.addBlockButton.setAttribute('aria-expanded', 'false');

    if (returnFocus) {
        elements.addBlockButton.focus();
    }
};

const openBlockMenu = () => {
    elements.blockMenu.hidden = false;
    elements.addBlockButton.setAttribute('aria-expanded', 'true');
    elements.blockMenu.querySelector('[role="menuitem"]')?.focus();
};

const setMode = (mode) => {
    const isEditor = mode === 'editor';
    elements.editorPanel.hidden = !isEditor;
    elements.previewPanel.hidden = isEditor;

    elements.modeButtons.forEach((button) => {
        const isActive = button.dataset.mode === mode;
        button.classList.toggle('is-active', isActive);
        button.setAttribute('aria-pressed', String(isActive));
    });

    closeBlockMenu();
};

const selectBlock = (index) => {
    if (!step.content.blocks[index]) {
        return;
    }

    selectedBlockIndex = index;
    renderBlocks();
    renderProperties();
};

const deleteBlock = (index) => {
    if (!step.content.blocks[index]) {
        return;
    }

    if (selectedBlockIndex === index) {
        if (index > 0) {
            selectedBlockIndex = index - 1;
        } else if (step.content.blocks.length > 1) {
            selectedBlockIndex = 0;
        } else {
            selectedBlockIndex = null;
        }
    } else if (selectedBlockIndex !== null && index < selectedBlockIndex) {
        selectedBlockIndex -= 1;
    }

    removeBlock(index);
};

const addNewBlock = (type) => {
    selectedBlockIndex = step.content.blocks.length;
    focusPropertiesAfterRender = true;
    addBlock(createBlock(type));
    closeBlockMenu();
};

const handleBlockListClick = (event) => {
    const card = event.target.closest('[data-block-index]');
    if (!card) {
        return;
    }

    const index = Number(card.dataset.blockIndex);
    if (event.target.closest('[data-block-action="delete"]')) {
        deleteBlock(index);
        return;
    }

    selectBlock(index);
};

const bindEvents = () => {
    elements.backButton.addEventListener('click', (event) => {
        if (window.history.length > 1) {
            event.preventDefault();
            window.history.back();
        }
    });

    elements.modeButtons.forEach((button) => {
        button.addEventListener('click', () => setMode(button.dataset.mode));
    });

    elements.layoutOptions.forEach((option) => {
        option.addEventListener('change', () => {
            if (option.checked) {
                setLayout(option.value);
            }
        });
    });

    elements.addBlockButton.addEventListener('click', () => {
        if (elements.blockMenu.hidden) {
            openBlockMenu();
        } else {
            closeBlockMenu();
        }
    });

    elements.blockMenu.addEventListener('click', (event) => {
        const menuItem = event.target.closest('[data-block-type]');
        if (menuItem) {
            addNewBlock(menuItem.dataset.blockType);
        }
    });

    elements.blockList.addEventListener('click', handleBlockListClick);
    elements.blockList.addEventListener('keydown', (event) => {
        if (
            (event.key === 'Enter' || event.key === ' ') &&
            !event.target.closest('[data-block-action]')
        ) {
            event.preventDefault();
            const card = event.target.closest('[data-block-index]');
            if (card) {
                selectBlock(Number(card.dataset.blockIndex));
            }
        }
    });

    document.addEventListener('click', (event) => {
        if (!event.target.closest('.add-block')) {
            closeBlockMenu();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !elements.blockMenu.hidden) {
            closeBlockMenu({ returnFocus: true });
        }
    });
};

const init = () => {
    if (!elements.root) {
        return;
    }

    renderBlockMenu();
    subscribeToStep(renderEditor);
    renderEditor();
    bindEvents();
};

init();
