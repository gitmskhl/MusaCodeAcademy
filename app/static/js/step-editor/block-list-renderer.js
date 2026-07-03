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

const createAction = (label, action, modifier = '') => {
    const button = document.createElement('button');
    button.className = `block-card__action ${modifier}`.trim();
    button.type = 'button';
    button.dataset.blockAction = action;
    button.textContent = label;
    return button;
};

const createBlockCard = (block, index) => {
    const definition = getBlockType(block.type);
    const label = definition?.label ?? block.type;

    const card = document.createElement('article');
    card.className = 'block-card';
    card.dataset.blockIndex = String(index);

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
    meta.textContent = `${label} block`;

    details.append(type, meta);
    identity.append(icon, details);

    const actions = document.createElement('div');
    actions.className = 'block-card__actions';
    actions.append(
        createAction('Edit', 'edit'),
        createAction('Delete', 'delete', 'block-card__action--danger')
    );

    card.append(identity, actions);
    return card;
};

export const renderBlockList = (container, blocks) => {
    container.replaceChildren();

    if (blocks.length === 0) {
        container.appendChild(createEmptyState());
        return;
    }

    const fragment = document.createDocumentFragment();
    blocks.forEach((block, index) => {
        fragment.appendChild(createBlockCard(block, index));
    });
    container.appendChild(fragment);
};
