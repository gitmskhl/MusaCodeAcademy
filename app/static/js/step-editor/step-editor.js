import { createBlock, getBlockTypes } from './block-types.js';
import { renderBlockList } from './block-list-renderer.js';
import { renderPreviewPlaceholder } from './preview.js';
import { addBlock, setLayout, step, subscribeToStep } from './step-state.js';

const elements = {
    root: document.querySelector('[data-step-editor]'),
    backButton: document.querySelector('[data-back-button]'),
    editorPanel: document.querySelector('[data-editor-panel]'),
    previewPanel: document.querySelector('[data-preview-panel]'),
    modeButtons: [...document.querySelectorAll('[data-mode]')],
    layoutOptions: [...document.querySelectorAll('[data-layout-option]')],
    blockList: document.querySelector('[data-block-list]'),
    addBlockButton: document.querySelector('[data-add-block-button]'),
    blockMenu: document.querySelector('[data-block-menu]'),
};

const renderEditor = () => {
    elements.layoutOptions.forEach((option) => {
        option.checked = option.value === step.layout;
    });
    renderBlockList(elements.blockList, step.content.blocks);
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
        if (!menuItem) {
            return;
        }

        addBlock(createBlock(menuItem.dataset.blockType));
        closeBlockMenu({ returnFocus: true });
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
    renderPreviewPlaceholder(elements.previewPanel);
    subscribeToStep(renderEditor);
    renderEditor();
    bindEvents();
};

init();
