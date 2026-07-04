import { getBlockType } from './block-types.js';
import { createBlockEditor } from './properties-panel.js';

const createEmptyState = () => {
    const emptyState = document.createElement('div');
    emptyState.className = 'block-list__empty';
    emptyState.innerHTML = `
        <div>
            <span class="block-list__empty-icon" aria-hidden="true">+</span>
            <strong>No content blocks yet</strong>
            <p>Add your first block below to start writing.</p>
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

const getPreviewText = (block, summary) => {
    const previewValues = {
        text: block.data.text,
        code: block.data.code,
        image: block.data.caption || block.data.alt || block.data.url,
    };
    const value = previewValues[block.type] ?? Object.values(block.data).find(
        (item) => typeof item === 'string' && item.trim()
    );

    return value?.trim() || summary;
};

const createBlockCard = (block, index, selectedIndex, onChange) => {
    const definition = getBlockType(block.type);
    const label = definition?.label ?? block.type;
    const summary = definition?.summarize?.(block.data) ?? `${label} block`;

    const card = document.createElement('article');
    card.className = 'block-card';
    card.dataset.blockIndex = String(index);
    card.tabIndex = index === selectedIndex ? -1 : 0;
    card.setAttribute('aria-label', `${label} block. ${summary}`);

    if (index === selectedIndex) {
        card.classList.add('is-selected');
        card.setAttribute('aria-current', 'true');
    }

    const dragHandle = document.createElement('span');
    dragHandle.className = 'block-card__drag-handle';
    dragHandle.title = 'Drag to reorder';
    dragHandle.setAttribute('aria-hidden', 'true');
    dragHandle.innerHTML =
        '<span></span><span></span><span></span><span></span><span></span><span></span>';

    const header = document.createElement('header');
    header.className = 'block-card__header';

    const icon = document.createElement('span');
    icon.className = 'block-card__type-icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = definition?.icon ?? '?';

    const type = document.createElement('p');
    type.className = 'block-card__type';
    type.textContent = label;

    const identity = document.createElement('div');
    identity.className = 'block-card__identity';
    identity.append(icon, type);

    const actions = document.createElement('div');
    actions.className = 'block-card__actions';
    actions.appendChild(createDeleteButton(label));

    header.append(dragHandle, identity, actions);
    card.appendChild(header);

    if (index === selectedIndex) {
        const editorWrap = document.createElement('div');
        editorWrap.className = 'block-card__editor';
        editorWrap.appendChild(createBlockEditor({
            block,
            index,
            onChange: (values) => onChange(index, values),
        }));
        card.appendChild(editorWrap);
    } else {
        const preview = document.createElement(
            block.type === 'code' ? 'pre' : 'p'
        );
        preview.className = `block-card__preview block-card__preview--${block.type}`;
        preview.textContent = getPreviewText(block, summary);
        card.appendChild(preview);
    }

    return card;
};

export const renderBlockList = (
    container,
    blocks,
    selectedIndex = null,
    onChange = () => {}
) => {
    container.replaceChildren();

    if (blocks.length === 0) {
        container.appendChild(createEmptyState());
        return;
    }

    const fragment = document.createDocumentFragment();
    blocks.forEach((block, index) => {
        fragment.appendChild(createBlockCard(block, index, selectedIndex, onChange));
    });
    container.appendChild(fragment);
};
