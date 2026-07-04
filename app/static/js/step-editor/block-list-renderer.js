import { renderCodeBlock } from './block-renderers/code-renderer.js';
import { renderImageBlock } from './block-renderers/image-renderer.js';
import { renderTextBlock } from './block-renderers/text-renderer.js';
import { renderCodeEditor } from './block-editors/code-editor.js';
import { renderImageEditor } from './block-editors/image-editor.js';
import { renderTextEditor } from './block-editors/text-editor.js';
import { renderUnavailableEditor } from './block-editors/unavailable-editor.js';
import { getBlockType } from './block-types.js';

const blockRenderers = new Map([
    ['text', renderTextBlock],
    ['image', renderImageBlock],
    ['code', renderCodeBlock],
]);

const blockEditors = new Map([
    ['text', renderTextEditor],
    ['image', renderImageEditor],
    ['code', renderCodeEditor],
]);

const createEmptyState = () => {
    const emptyState = document.createElement('div');
    emptyState.className = 'block-list__empty';
    emptyState.innerHTML = `
        <div>
            <span class="block-list__empty-icon" aria-hidden="true">+</span>
            <strong>Start your document</strong>
            <p>Add a text, image, or code block below.</p>
        </div>
    `;
    return emptyState;
};

const createDeleteButton = (blockLabel) => {
    const button = document.createElement('button');
    button.className = 'block-card__delete';
    button.type = 'button';
    button.dataset.blockAction = 'delete';
    button.setAttribute('aria-label', `Delete ${blockLabel} block`);
    button.innerHTML = `
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13M10 11v5M14 11v5"/>
        </svg>
    `;
    return button;
};

const renderUnknownBlock = (block) => {
    const fallback = document.createElement('p');
    fallback.className = 'rendered-block__placeholder';
    fallback.textContent = `Rendering is unavailable for “${block.type}” blocks.`;
    return fallback;
};

const createControls = (label) => {
    const controls = document.createElement('div');
    controls.className = 'block-card__controls';

    const dragHandle = document.createElement('button');
    dragHandle.className = 'block-card__drag-handle';
    dragHandle.type = 'button';
    dragHandle.draggable = true;
    dragHandle.dataset.dragHandle = '';
    dragHandle.title = 'Drag to reorder';
    dragHandle.setAttribute('aria-label', `Move ${label} block`);
    dragHandle.innerHTML =
        '<span></span><span></span><span></span><span></span><span></span><span></span>';

    const type = document.createElement('span');
    type.className = 'block-card__type';
    type.textContent = label;

    controls.append(dragHandle, type, createDeleteButton(label));
    return controls;
};

const createBlockCard = ({
    block,
    index,
    selectedIndex,
    editingIndex,
    onChange,
}) => {
    const definition = getBlockType(block.type);
    const label = definition?.label ?? block.type;
    const summary = definition?.summarize?.(block.data) ?? `${label} block`;
    const isSelected = index === selectedIndex;
    const isEditing = index === editingIndex;

    const card = document.createElement('article');
    card.className = `block-card block-card--${block.type}`;
    card.dataset.blockIndex = String(index);
    card.tabIndex = isSelected ? -1 : 0;
    card.setAttribute('aria-label', `${label} block. ${summary}`);
    if (isSelected) {
        card.classList.add('is-selected');
        card.setAttribute('aria-current', 'true');
    }
    if (isEditing) {
        card.classList.add('is-editing');
    }

    card.appendChild(createControls(label));

    const content = document.createElement('div');
    content.className = 'block-card__content';
    content.dataset.blockContent = '';

    const shouldShowEditor =
        isEditing ||
        (isSelected && (block.type === 'image' || block.type === 'code'));
    if (shouldShowEditor) {
        const editor = blockEditors.get(block.type) ?? renderUnavailableEditor;
        content.appendChild(editor({
            block,
            index,
            label,
            onChange: (values) => onChange(index, values),
        }));
    } else {
        const renderer = blockRenderers.get(block.type) ?? renderUnknownBlock;
        content.appendChild(renderer(block));
    }

    card.appendChild(content);
    return card;
};

export const renderBlockList = (
    container,
    blocks,
    {
        selectedIndex = null,
        editingIndex = null,
        onChange = () => {},
    } = {}
) => {
    container.replaceChildren();

    if (blocks.length === 0) {
        container.appendChild(createEmptyState());
        return;
    }

    const fragment = document.createDocumentFragment();
    blocks.forEach((block, index) => {
        fragment.appendChild(createBlockCard({
            block,
            index,
            selectedIndex,
            editingIndex,
            onChange,
        }));
    });
    container.appendChild(fragment);
};
