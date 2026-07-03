import { getBlockType } from './block-types.js';
import { renderTextEditor } from './block-editors/text-editor.js';
import { renderUnavailableEditor } from './block-editors/unavailable-editor.js';

const editorRenderers = new Map([
    ['text', renderTextEditor],
    ['image', renderUnavailableEditor],
    ['code', renderUnavailableEditor],
]);

const createEmptyState = () => {
    const emptyState = document.createElement('div');
    emptyState.className = 'properties-panel__empty';
    emptyState.innerHTML = `
        <span class="properties-panel__empty-icon" aria-hidden="true">⌁</span>
        <p>No block selected.</p>
    `;
    return emptyState;
};

const createHeader = (block, index) => {
    const definition = getBlockType(block.type);
    const label = definition?.label ?? block.type;

    const header = document.createElement('header');
    header.className = 'properties-panel__header';

    const heading = document.createElement('h2');
    heading.textContent = `${label} properties`;

    const position = document.createElement('span');
    position.className = 'properties-panel__position';
    position.textContent = `Block ${index + 1}`;

    header.append(heading, position);
    return { header, definition, label };
};

export const registerBlockEditor = (type, renderer) => {
    editorRenderers.set(type, renderer);
};

export const renderPropertiesPanel = (
    container,
    { block, index, onChange, focusFirstField = false }
) => {
    if (!block) {
        container.replaceChildren(createEmptyState());
        return;
    }

    const { header, definition, label } = createHeader(block, index);
    const renderer = editorRenderers.get(block.type) ?? renderUnavailableEditor;
    const editor = renderer({
        block,
        index,
        label,
        definition,
        onChange,
    });

    container.replaceChildren(header, editor);

    if (focusFirstField) {
        container.querySelector('[data-properties-first-field]')?.focus();
    }
};
