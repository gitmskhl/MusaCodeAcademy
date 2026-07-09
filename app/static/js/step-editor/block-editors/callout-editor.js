import { createMarkdownTextarea } from './text-editor.js';

const calloutVariants = [
    ['info', 'Info'],
    ['tip', 'Tip'],
    ['important', 'Important'],
    ['warning', 'Warning'],
    ['error', 'Error'],
];

export const renderCalloutEditor = ({ block, index, onChange }) => {
    const editor = document.createElement('div');
    editor.className = 'inline-callout-editor';

    const controls = document.createElement('div');
    controls.className = 'inline-callout-editor__controls';

    const variantLabel = document.createElement('label');
    variantLabel.className = 'inline-callout-editor__field';
    variantLabel.htmlFor = `callout-variant-${index}`;

    const variantText = document.createElement('span');
    variantText.className = 'inline-callout-editor__label';
    variantText.textContent = 'Variant';

    const variant = document.createElement('select');
    variant.className = 'inline-callout-editor__select';
    variant.id = variantLabel.htmlFor;
    calloutVariants.forEach(([value, label]) => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = label;
        variant.appendChild(option);
    });
    variant.value = block.data.variant ?? 'info';
    variant.dataset.propertiesFirstField = '';
    variant.addEventListener('change', () => {
        onChange({ variant: variant.value });
    });
    variantLabel.append(variantText, variant);

    const titleLabel = document.createElement('label');
    titleLabel.className = 'inline-callout-editor__field';
    titleLabel.htmlFor = `callout-title-${index}`;

    const titleText = document.createElement('span');
    titleText.className = 'inline-callout-editor__label';
    titleText.textContent = 'Title';

    const title = document.createElement('input');
    title.className = 'inline-callout-editor__input';
    title.id = titleLabel.htmlFor;
    title.type = 'text';
    title.placeholder = 'Optional title';
    title.value = block.data.title ?? '';
    title.addEventListener('input', () => {
        onChange({ title: title.value });
    });
    titleLabel.append(titleText, title);

    const textarea = createMarkdownTextarea({
        id: `callout-content-${index}`,
        value: block.data.content,
        placeholder: 'Write callout content with Markdown...',
        ariaLabel: 'Callout Markdown content',
        onChange: (value) => onChange({ content: value }),
    });

    controls.append(variantLabel, titleLabel);
    editor.append(controls, textarea);
    return editor;
};
