import {
    normalizeKinescopeEmbedUrl,
    normalizeVideoAspectRatio,
    renderVideoBlock,
} from '../../step-renderer/block-renderers/video-renderer.js';

const aspectRatioOptions = [
    ['16:9', '16:9'],
    ['4:3', '4:3'],
    ['1:1', '1:1'],
    ['9:16', '9:16'],
];

const setStatus = (status, message, { error = false } = {}) => {
    status.classList.toggle('is-error', error);
    status.textContent = message;
};

const createFieldLabel = ({ className, htmlFor, label }) => {
    const field = document.createElement('label');
    field.className = className;
    field.htmlFor = htmlFor;

    const text = document.createElement('span');
    text.className = 'inline-video-editor__label';
    text.textContent = label;
    field.appendChild(text);

    return field;
};

export const renderVideoEditor = ({ block, index, onChange }) => {
    const previewData = {
        provider: block.data.provider ?? 'kinescope',
        embed_url: block.data.embed_url ?? '',
        title: block.data.title ?? '',
        caption: block.data.caption ?? '',
        aspect_ratio: normalizeVideoAspectRatio(block.data.aspect_ratio),
    };

    const editor = document.createElement('div');
    editor.className = 'inline-video-editor';

    const fields = document.createElement('div');
    fields.className = 'inline-video-editor__fields';

    const embedField = createFieldLabel({
        className: 'inline-video-editor__field inline-video-editor__field--embed',
        htmlFor: `video-embed-${index}`,
        label: 'Встраивание Kinescope',
    });

    const embedInput = document.createElement('textarea');
    embedInput.className = 'inline-video-editor__textarea';
    embedInput.id = embedField.htmlFor;
    embedInput.rows = 3;
    embedInput.value = previewData.embed_url;
    embedInput.placeholder =
        '<iframe src="https://kinescope.io/embed/..." ...></iframe>';
    embedInput.dataset.propertiesFirstField = '';
    embedInput.setAttribute('aria-label', 'iframe Kinescope или ссылка для встраивания');
    embedField.appendChild(embedInput);

    const titleField = createFieldLabel({
        className: 'inline-video-editor__field',
        htmlFor: `video-title-${index}`,
        label: 'Заголовок',
    });
    const titleInput = document.createElement('input');
    titleInput.className = 'inline-video-editor__input';
    titleInput.id = titleField.htmlFor;
    titleInput.type = 'text';
    titleInput.value = previewData.title;
    titleInput.placeholder = 'Необязательный заголовок';
    titleField.appendChild(titleInput);

    const aspectField = createFieldLabel({
        className: 'inline-video-editor__field',
        htmlFor: `video-aspect-${index}`,
        label: 'Соотношение сторон',
    });
    const aspectSelect = document.createElement('select');
    aspectSelect.className = 'inline-video-editor__select';
    aspectSelect.id = aspectField.htmlFor;
    aspectRatioOptions.forEach(([value, label]) => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = label;
        aspectSelect.appendChild(option);
    });
    aspectSelect.value = previewData.aspect_ratio;
    aspectField.appendChild(aspectSelect);

    const captionField = createFieldLabel({
        className: 'inline-video-editor__field inline-video-editor__field--caption',
        htmlFor: `video-caption-${index}`,
        label: 'Подпись',
    });
    const captionInput = document.createElement('input');
    captionInput.className = 'inline-video-editor__input';
    captionInput.id = captionField.htmlFor;
    captionInput.type = 'text';
    captionInput.value = previewData.caption;
    captionInput.placeholder = 'Необязательная подпись';
    captionField.appendChild(captionInput);

    const status = document.createElement('p');
    status.className = 'inline-video-editor__status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');

    const preview = document.createElement('div');
    preview.className = 'inline-video-editor__preview';

    const renderPreview = () => {
        preview.replaceChildren(renderVideoBlock({
            type: 'video',
            data: previewData,
        }));
    };

    const applyChange = (values) => {
        Object.assign(previewData, values);
        onChange(values);
        renderPreview();
    };

    embedInput.addEventListener('input', () => {
        const rawValue = embedInput.value.trim();
        if (!rawValue) {
            setStatus(status, '');
            applyChange({ embed_url: '' });
            return;
        }

        const embedUrl = normalizeKinescopeEmbedUrl(rawValue);
        if (!embedUrl) {
            setStatus(
                status,
                'Используйте iframe Kinescope или ссылку https://kinescope.io/embed/...',
                { error: true }
            );
            applyChange({ embed_url: '' });
            return;
        }

        if (rawValue.toLowerCase().includes('<iframe')) {
            embedInput.value = embedUrl;
        }
        setStatus(status, '');
        applyChange({ provider: 'kinescope', embed_url: embedUrl });
    });

    titleInput.addEventListener('input', () => {
        applyChange({ title: titleInput.value });
    });

    aspectSelect.addEventListener('change', () => {
        applyChange({ aspect_ratio: aspectSelect.value });
    });

    captionInput.addEventListener('input', () => {
        applyChange({ caption: captionInput.value });
    });

    fields.append(embedField, titleField, aspectField, captionField);
    editor.append(fields, status, preview);
    renderPreview();
    return editor;
};
