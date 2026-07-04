const createField = ({ id, labelText, value, placeholder, first = false }) => {
    const field = document.createElement('label');
    field.className = 'property-field';
    field.htmlFor = id;

    const label = document.createElement('span');
    label.className = 'property-field__label';
    label.textContent = labelText;

    const input = document.createElement('input');
    input.className = 'property-field__input';
    input.id = id;
    input.type = 'text';
    input.value = value;
    input.placeholder = placeholder;
    if (first) {
        input.dataset.propertiesFirstField = '';
    }

    field.append(label, input);
    return { field, input };
};

export const renderImageEditor = ({ block, index, onChange }) => {
    const editor = document.createElement('div');
    editor.className = 'block-properties block-properties--image';

    const url = createField({
        id: `image-url-${index}`,
        labelText: 'Image URL',
        value: block.data.url ?? '',
        placeholder: 'https://example.com/image.jpg',
        first: true,
    });
    const alt = createField({
        id: `image-alt-${index}`,
        labelText: 'Alternative text',
        value: block.data.alt ?? '',
        placeholder: 'Describe the image',
    });
    const caption = createField({
        id: `image-caption-${index}`,
        labelText: 'Caption',
        value: block.data.caption ?? '',
        placeholder: 'Optional caption',
    });

    url.input.addEventListener('input', () => onChange({ url: url.input.value }));
    alt.input.addEventListener('input', () => onChange({ alt: alt.input.value }));
    caption.input.addEventListener('input', () => {
        onChange({ caption: caption.input.value });
    });

    editor.append(url.field, alt.field, caption.field);
    return editor;
};
