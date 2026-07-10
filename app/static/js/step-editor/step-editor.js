import { createBlock, getBlockTypes } from './block-types.js';
import { renderBlockList } from './block-list-renderer.js';
import { getStepBlocks } from '../step-renderer/layout-renderers.js';
import { registerImageSource } from '../step-renderer/image-sources.js';
import {
    addBlock,
    getBlocks,
    loadStepContent,
    moveBlock,
    removeBlock,
    setLayout,
    step,
    subscribeToStep,
    updateBlockData,
} from './step-state.js';

const TOKEN_KEY = 'musa_code_academy_token';

const getToken = () => localStorage.getItem(TOKEN_KEY);

const clearToken = () => localStorage.removeItem(TOKEN_KEY);

const redirectHome = () => {
    window.location.href = '/dashboard';
};

const checkAdminAccess = async () => {
    const token = getToken();
    if (!token) {
        redirectHome();
        return false;
    }

    const response = await fetch('/api/users/me', {
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });

    if (response.status === 401) {
        clearToken();
        redirectHome();
        return false;
    }

    if (!response.ok) {
        redirectHome();
        return false;
    }

    const user = await response.json();
    if (user.role !== 'admin') {
        redirectHome();
        return false;
    }

    return true;
};

const elements = {
    root: document.querySelector('[data-step-editor]'),
    backButton: document.querySelector('[data-back-button]'),
    saveButton: document.querySelector('[data-save-button]'),
    taskButton: document.querySelector('[data-task-button]'),
    saveStatus: document.querySelector('[data-save-status]'),
    layoutOptions: [...document.querySelectorAll('[data-layout-option]')],
    blockList: document.querySelector('[data-block-list]'),
    addBlockButton: document.querySelector('[data-add-block-button]'),
    blockMenu: document.querySelector('[data-block-menu]'),
};

let selectedBlockIndex = null;
let editingBlockIndex = null;
let focusEditorAfterRender = false;
let draggedBlockIndex = null;
let dropInsertionIndex = null;
let saveStatusTimer = null;

const dropPlaceholder = document.createElement('div');
dropPlaceholder.className = 'block-drop-placeholder';
dropPlaceholder.dataset.dropPlaceholder = '';
dropPlaceholder.setAttribute('aria-hidden', 'true');

const renderLayout = () => {
    elements.layoutOptions.forEach((option) => {
        option.checked = option.value === step.content.layout;
    });
};

const handleBlockChange = (index, values) => {
    updateBlockData(index, values);

    // An uploaded image changes from a placeholder into the shared image
    // renderer, so that structural update needs one immediate repaint.
    if (Object.hasOwn(values, 'file_id')) {
        focusEditorAfterRender = true;
        renderBlocks();
    }
};

const renderBlocks = () => {
    renderBlockList(elements.blockList, step.content, {
        selectedIndex: selectedBlockIndex,
        editingIndex: editingBlockIndex,
        onChange: handleBlockChange,
    });

    if (focusEditorAfterRender) {
        elements.blockList.querySelector('[data-properties-first-field]')?.focus();
        focusEditorAfterRender = false;
    }
};

const renderEditor = (_currentStep = step, change = { type: 'initial-render' }) => {
    renderLayout();

    // Inputs update the state as the user types. Replacing their DOM here would
    // lose focus and the caret, so only structural changes repaint the document.
    if (change.type !== 'block-data-updated') {
        renderBlocks();
    }
};

const setSaveStatus = (message, { error = false } = {}) => {
    window.clearTimeout(saveStatusTimer);
    elements.saveStatus.classList.toggle('is-error', error);
    elements.saveStatus.textContent = message;
};

const getResponseErrorMessage = async (response, fallback) => {
    try {
        const data = await response.json();
        if (Array.isArray(data.detail)) {
            return data.detail
                .map((item) => {
                    const field = item.loc?.at(-1);
                    return field ? `${field}: ${item.msg}` : item.msg;
                })
                .join(' ');
        }
        if (typeof data.detail === 'string') {
            return data.detail;
        }
    } catch {
        // The response has no JSON error body.
    }
    return `${fallback} (${response.status}).`;
};

const setEditorLoading = (loading) => {
    elements.saveButton.disabled = loading;
    if (elements.taskButton) {
        elements.taskButton.disabled = loading;
    }
    elements.addBlockButton.disabled = loading;
    elements.layoutOptions.forEach((option) => {
        option.disabled = loading;
    });
};

const loadTaskButton = async () => {
    if (!elements.taskButton) {
        return;
    }

    const stepId = Number(elements.root.dataset.stepId);
    if (!Number.isInteger(stepId) || stepId <= 0) {
        return;
    }

    const token = getToken();
    if (!token) {
        return;
    }

    elements.taskButton.textContent = 'Создать задачу';
    elements.taskButton.hidden = false;

    let response = await fetch(
        `/api/steps/${encodeURIComponent(stepId)}/task`,
        { headers: { Authorization: `Bearer ${token}` } }
    );
    if (response.status >= 500) {
        response = await fetch(
            `/api/tasks/admin/by-step/${encodeURIComponent(stepId)}`,
            { headers: { Authorization: `Bearer ${token}` } }
        );
    }

    if (response.status === 200) {
        elements.taskButton.textContent = 'Редактировать задачу';
        elements.taskButton.hidden = false;
        return;
    }

    if (response.status === 404) {
        elements.taskButton.textContent = 'Создать задачу';
        elements.taskButton.hidden = false;
    }
};

const loadImageSources = async (content, token) => {
    const fileIds = [
        ...new Set(
            getStepBlocks(content)
                .filter((block) => block.type === 'image')
                .map((block) => block.data.file_id)
        ),
    ];
    if (fileIds.length === 0) {
        return;
    }

    const params = new URLSearchParams();
    fileIds.forEach((fileId) => params.append('ids', String(fileId)));
    const response = await fetch(`/api/files?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
        throw new Error(
            await getResponseErrorMessage(response, 'Failed to load images')
        );
    }

    const files = await response.json();
    files.forEach((file) => registerImageSource(file.id, file.url));
};

const loadStep = async () => {
    const stepId = Number(elements.root.dataset.stepId);
    if (!Number.isInteger(stepId) || stepId <= 0) {
        throw new Error('Invalid step ID.');
    }

    const token = getToken();
    if (!token) {
        throw new Error('Sign in again to load the step.');
    }

    const response = await fetch(
        `/api/steps/${encodeURIComponent(stepId)}/admin`,
        { headers: { Authorization: `Bearer ${token}` } }
    );
    if (!response.ok) {
        throw new Error(
            await getResponseErrorMessage(response, 'Failed to load step')
        );
    }

    const loadedStep = await response.json();
    let imageError = null;
    try {
        await loadImageSources(loadedStep.content, token);
    } catch (error) {
        imageError = error;
    }

    loadStepContent(loadedStep.content);
    if (imageError) {
        setSaveStatus(imageError.message, { error: true });
    } else {
        setSaveStatus('');
    }
};

const saveStep = async () => {
    const stepId = Number(elements.root.dataset.stepId);
    if (!Number.isInteger(stepId) || stepId <= 0) {
        setSaveStatus('Invalid step ID.', { error: true });
        return;
    }

    const token = getToken();
    if (!token) {
        setSaveStatus('Sign in again to save the step.', { error: true });
        return;
    }

    const savedSnapshot = JSON.stringify(step);
    elements.saveButton.disabled = true;
    elements.saveButton.textContent = 'Saving…';
    setSaveStatus('');

    try {
        const response = await fetch(
            `/api/steps/${encodeURIComponent(stepId)}/admin`,
            {
                method: 'PATCH',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: savedSnapshot,
            }
        );
        if (!response.ok) {
            throw new Error(
                await getResponseErrorMessage(response, 'Failed to save step')
            );
        }

        if (JSON.stringify(step) === savedSnapshot) {
            elements.saveButton.textContent = 'Saved';
            setSaveStatus('Changes saved.');
            saveStatusTimer = window.setTimeout(() => {
                elements.saveButton.textContent = 'Save';
                elements.saveStatus.textContent = '';
            }, 1800);
        } else {
            elements.saveButton.textContent = 'Save';
            setSaveStatus('Saved. There are newer unsaved changes.');
        }
    } catch (error) {
        elements.saveButton.textContent = 'Save';
        setSaveStatus(
            error instanceof Error && error.message
                ? error.message
                : 'Failed to save step.',
            { error: true }
        );
    } finally {
        elements.saveButton.disabled = false;
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

const activateBlock = (index, { focusEditor = false } = {}) => {
    const block = getBlocks()[index];
    if (!block) {
        return;
    }

    const shouldEditText = block.type === 'text' || block.type === 'callout';
    if (
        selectedBlockIndex === index &&
        editingBlockIndex === (shouldEditText ? index : null)
    ) {
        return;
    }

    selectedBlockIndex = index;
    editingBlockIndex = shouldEditText ? index : null;
    focusEditorAfterRender = focusEditor || shouldEditText;
    renderBlocks();
};

const deactivateBlock = () => {
    if (selectedBlockIndex === null && editingBlockIndex === null) {
        return;
    }
    selectedBlockIndex = null;
    editingBlockIndex = null;
    renderBlocks();
};

const deleteBlock = (index) => {
    if (!getBlocks()[index]) {
        return;
    }

    if (selectedBlockIndex === index) {
        selectedBlockIndex = null;
        editingBlockIndex = null;
    } else if (selectedBlockIndex !== null && index < selectedBlockIndex) {
        selectedBlockIndex -= 1;
        if (editingBlockIndex !== null) {
            editingBlockIndex -= 1;
        }
    }
    removeBlock(index);
};

const addNewBlock = (type) => {
    selectedBlockIndex = getBlocks().length;
    editingBlockIndex =
        type === 'text' || type === 'callout' ? selectedBlockIndex : null;
    focusEditorAfterRender = true;
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
    if (event.target.closest('[data-drag-handle]')) {
        selectedBlockIndex = index;
        editingBlockIndex = null;
        renderBlocks();
        return;
    }

    activateBlock(index, { focusEditor: true });
};

const clearDropIndicators = () => {
    dropInsertionIndex = null;
    dropPlaceholder.remove();
};

const remapIndexAfterMove = (index, fromIndex, toIndex) => {
    if (index === null || fromIndex === toIndex) {
        return index;
    }
    if (index === fromIndex) {
        return toIndex;
    }
    if (fromIndex < toIndex && index > fromIndex && index <= toIndex) {
        return index - 1;
    }
    if (fromIndex > toIndex && index >= toIndex && index < fromIndex) {
        return index + 1;
    }
    return index;
};

const bindDragAndDrop = () => {
    const showDropPlaceholder = (card, after) => {
        const targetIndex = Number(card.dataset.blockIndex);
        dropInsertionIndex = targetIndex + (after ? 1 : 0);
        card.parentElement.insertBefore(
            dropPlaceholder,
            after ? card.nextSibling : card
        );
    };

    elements.blockList.addEventListener('dragstart', (event) => {
        const handle = event.target.closest('[data-drag-handle]');
        const card = handle?.closest('[data-block-index]');
        if (!card) {
            event.preventDefault();
            return;
        }

        draggedBlockIndex = Number(card.dataset.blockIndex);
        card.classList.add('is-dragging');
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', String(draggedBlockIndex));
        event.dataTransfer.setDragImage(card, 18, 18);
    });

    elements.blockList.addEventListener('dragover', (event) => {
        if (draggedBlockIndex === null) {
            return;
        }

        if (event.target.closest('[data-drop-placeholder]')) {
            event.preventDefault();
            event.dataTransfer.dropEffect = 'move';
            return;
        }

        const card = event.target.closest('[data-block-index]');
        if (!card) {
            const cards = [
                ...elements.blockList.querySelectorAll('[data-block-index]'),
            ];
            const lastCard = cards.at(-1);
            if (
                lastCard &&
                event.clientY >= lastCard.getBoundingClientRect().bottom
            ) {
                event.preventDefault();
                showDropPlaceholder(lastCard, true);
                event.dataTransfer.dropEffect = 'move';
            }
            return;
        }

        event.preventDefault();
        const cardRect = card.getBoundingClientRect();
        const after = elements.blockList.classList.contains(
            'step-renderer--two-columns'
        )
            ? event.clientX > cardRect.left + cardRect.width / 2
            : event.clientY > cardRect.top + cardRect.height / 2;
        showDropPlaceholder(card, after);
        event.dataTransfer.dropEffect = 'move';
    });

    elements.blockList.addEventListener('drop', (event) => {
        if (draggedBlockIndex === null || dropInsertionIndex === null) {
            return;
        }

        event.preventDefault();
        const fromIndex = draggedBlockIndex;
        let toIndex = dropInsertionIndex;
        if (fromIndex < toIndex) {
            toIndex -= 1;
        }
        toIndex = Math.max(0, Math.min(getBlocks().length - 1, toIndex));

        selectedBlockIndex = remapIndexAfterMove(
            selectedBlockIndex,
            fromIndex,
            toIndex
        );
        editingBlockIndex = remapIndexAfterMove(
            editingBlockIndex,
            fromIndex,
            toIndex
        );
        clearDropIndicators();
        draggedBlockIndex = null;
        if (!moveBlock(fromIndex, toIndex)) {
            renderBlocks();
        }
    });

    elements.blockList.addEventListener('dragend', () => {
        draggedBlockIndex = null;
        clearDropIndicators();
        elements.blockList.querySelector('.is-dragging')?.classList.remove(
            'is-dragging'
        );
    });
};

const bindEvents = () => {
    elements.saveButton.addEventListener('click', saveStep);

    elements.taskButton?.addEventListener('click', () => {
        const stepId = Number(elements.root.dataset.stepId);
        if (Number.isInteger(stepId) && stepId > 0) {
            window.location.href = `/admin/steps/${encodeURIComponent(stepId)}/task`;
        }
    });

    elements.backButton.addEventListener('click', (event) => {
        if (window.history.length > 1) {
            event.preventDefault();
            window.history.back();
        }
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
        const card = event.target.closest('[data-block-index]');
        if (
            (event.key === 'Enter' || event.key === ' ') &&
            card &&
            event.target === card
        ) {
            event.preventDefault();
            activateBlock(Number(card.dataset.blockIndex), {
                focusEditor: true,
            });
        }
    });

    elements.blockList.addEventListener('focusout', (event) => {
        const card = event.target.closest('[data-block-index]');
        if (!card || Number(card.dataset.blockIndex) !== editingBlockIndex) {
            return;
        }
        const index = Number(card.dataset.blockIndex);
        requestAnimationFrame(() => {
            const currentCard = elements.blockList.querySelector(
                `[data-block-index="${index}"]`
            );
            if (
                editingBlockIndex === index &&
                !currentCard?.contains(document.activeElement)
            ) {
                editingBlockIndex = null;
                renderBlocks();
            }
        });
    });

    document.addEventListener('click', (event) => {
        if (!event.target.closest('.add-block')) {
            closeBlockMenu();
        }
        if (
            !event.target.closest('[data-block-index]') &&
            !event.target.closest('.add-block') &&
            !event.target.closest('.layout-options')
        ) {
            deactivateBlock();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') {
            return;
        }
        if (!elements.blockMenu.hidden) {
            closeBlockMenu({ returnFocus: true });
        } else if (editingBlockIndex !== null) {
            editingBlockIndex = null;
            renderBlocks();
        }
    });

    bindDragAndDrop();
};

const init = async () => {
    if (!elements.root) {
        return;
    }

    try {
        const hasAccess = await checkAdminAccess();
        if (!hasAccess) {
            return;
        }
    } catch {
        redirectHome();
        return;
    }

    renderBlockMenu();
    subscribeToStep(renderEditor);
    bindEvents();
    setEditorLoading(true);
    setSaveStatus('Loading step...');

    try {
        await loadStep();
        await loadTaskButton();
        setEditorLoading(false);
    } catch (error) {
        setSaveStatus(
            error instanceof Error && error.message
                ? error.message
                : 'Failed to load step.',
            { error: true }
        );
    }
};

init();
