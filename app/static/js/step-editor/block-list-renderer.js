import { getBlockType } from './block-types.js';

const createEmptyState = () => {
    const emptyState = document.createElement('div');
    emptyState.className = 'block-list__empty';
    emptyState.innerHTML = `
        <div>
            <span class="block-list__empty-icon" aria-hidden="true">+</span>
            <strong>No content blocks yet</strong>
            <p>Use “Add block” to start building this step.</p>
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

const createBlockCard = (block, index, selectedIndex) => {
    const definition = getBlockType(block.type);
    const label = definition?.label ?? block.type;
    const summary = definition?.summarize?.(block.data) ?? `${label} block`;

    const card = document.createElement('article');
    card.className = 'block-card';
    card.dataset.blockIndex = String(index);
    card.tabIndex = 0;
    card.setAttribute('aria-label', `${label} block. ${summary}`);

    if (index === selectedIndex) {
        card.classList.add('is-selected');
        card.setAttribute('aria-current', 'true');
    }

    const dragHandle = document.createElement('span');
    dragHandle.className = 'block-card__drag-handle';
    dragHandle.title = 'Drag to reorder (coming later)';
    dragHandle.setAttribute('aria-hidden', 'true');
    dragHandle.innerHTML =
        '<span></span><span></span><span></span><span></span><span></span><span></span>';

    const identity = document.createElement('div');
    identity.className = 'block-card__identity';

    const icon = document.createElement('span');
    icon.className = 'block-card__type-icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = definition?.icon ?? '?';

    const details = document.createElement('div');
    const type = document.createElement('p');
    type.className = 'block-card__type';
    type.textContent = label;

    const meta = document.createElement('p');
    meta.className = 'block-card__meta';
    meta.textContent = summary;
    meta.title = summary;

    details.append(type, meta);
    identity.append(icon, details);

    card.append(dragHandle, identity, createDeleteButton(label));
    return card;
};

export const renderBlockList = (container, blocks, selectedIndex = null) => {
    container.replaceChildren();

    if (blocks.length === 0) {
        container.appendChild(createEmptyState());
        return;
    }

    const fragment = document.createDocumentFragment();
    blocks.forEach((block, index) => {
        fragment.appendChild(createBlockCard(block, index, selectedIndex));
    });
    container.appendChild(fragment);
};
