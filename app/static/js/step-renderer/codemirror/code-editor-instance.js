import { createCodeEditorView } from './code-editor-view.js';

const blockEditors = new WeakMap();

const createBlockEditor = (block, onChange, language) => {
    const element = document.createElement('div');
    element.className = 'code-editor';
    element.tabIndex = -1;

    const controller = createCodeEditorView({
        parent: element,
        document: block.data.code ?? '',
        language: language ?? block.data.language ?? '',
        onChange,
    });
    element.addEventListener('focus', () => controller.focus());

    return { controller, element };
};

export const mountCodeEditor = ({
    block,
    index,
    language = null,
    parent,
    editable,
    onChange,
}) => {
    let blockEditor = blockEditors.get(block);
    if (!blockEditor) {
        blockEditor = createBlockEditor(block, onChange, language);
        blockEditors.set(block, blockEditor);
    }

    const { controller, element } = blockEditor;
    const scroller = element.querySelector('.cm-scroller');
    const scrollPosition = {
        left: scroller.scrollLeft,
        top: scroller.scrollTop,
    };
    controller.setOnChange(onChange);
    controller.setLanguage(language ?? block.data.language ?? '');
    controller.setEditable(editable);

    element.id = `code-block-${index}`;
    element.classList.toggle('code-editor--readonly', !editable);
    if (editable) {
        element.dataset.propertiesFirstField = '';
    } else {
        delete element.dataset.propertiesFirstField;
    }

    parent.appendChild(element);
    scroller.scrollLeft = scrollPosition.left;
    scroller.scrollTop = scrollPosition.top;
    requestAnimationFrame(() => {
        scroller.scrollLeft = scrollPosition.left;
        scroller.scrollTop = scrollPosition.top;
    });
    return blockEditor;
};
