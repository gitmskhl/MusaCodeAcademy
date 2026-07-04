import {
    getImageSource,
    getUploadedImageUrl,
    registerImageSource,
} from '../image-sources.js';

const UPLOAD_ENDPOINT = '/api/files/images';
const TOKEN_KEY = 'musa_code_academy_token';

const clampWidth = (value) => {
    const width = Number(value);
    return Number.isFinite(width) ? Math.min(100, Math.max(10, width)) : 100;
};

const createPlaceholder = () => {
    const placeholder = document.createElement('div');
    placeholder.className = 'image-editor__placeholder';
    placeholder.innerHTML = `
        <span aria-hidden="true">▧</span>
        <p>No image uploaded</p>
    `;
    return placeholder;
};

const getErrorMessage = async (response) => {
    try {
        const data = await response.json();
        if (Array.isArray(data.detail)) {
            return data.detail.map((item) => item.msg).join(' ');
        }
        return data.detail || 'Image upload failed.';
    } catch {
        return 'Image upload failed.';
    }
};

export const renderImageEditor = ({ block, index, onChange }) => {
    // Remove fields used by the former URL-based image block.
    delete block.data.url;
    delete block.data.alt;
    block.data.width = clampWidth(block.data.width);
    block.data.caption = block.data.caption ?? '';

    const editor = document.createElement('div');
    editor.className = 'block-properties block-properties--image';

    const preview = document.createElement('div');
    preview.className = 'image-editor__preview';

    const fileInput = document.createElement('input');
    fileInput.className = 'image-editor__file-input';
    fileInput.id = `image-file-${index}`;
    fileInput.type = 'file';
    fileInput.accept = 'image/*';

    const uploadButton = document.createElement('button');
    uploadButton.className = 'image-editor__upload-button';
    uploadButton.type = 'button';
    uploadButton.dataset.propertiesFirstField = '';

    const status = document.createElement('p');
    status.className = 'image-editor__status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');

    const captionField = document.createElement('label');
    captionField.className = 'property-field';
    captionField.htmlFor = `image-caption-${index}`;
    captionField.innerHTML =
        '<span class="property-field__label">Caption</span>';

    const captionInput = document.createElement('input');
    captionInput.className = 'property-field__input';
    captionInput.id = `image-caption-${index}`;
    captionInput.type = 'text';
    captionInput.value = block.data.caption;
    captionInput.placeholder = 'Optional caption';
    captionField.appendChild(captionInput);

    const widthField = document.createElement('div');
    widthField.className = 'image-editor__width-field';

    const widthHeader = document.createElement('div');
    widthHeader.className = 'image-editor__width-header';
    const widthLabel = document.createElement('label');
    widthLabel.className = 'property-field__label';
    widthLabel.htmlFor = `image-width-${index}`;
    widthLabel.textContent = 'Width';
    const widthValue = document.createElement('output');
    widthValue.className = 'image-editor__width-value';
    widthValue.htmlFor = `image-width-${index}`;
    widthHeader.append(widthLabel, widthValue);

    const widthInput = document.createElement('input');
    widthInput.className = 'image-editor__width-slider';
    widthInput.id = `image-width-${index}`;
    widthInput.type = 'range';
    widthInput.min = '10';
    widthInput.max = '100';
    widthInput.step = '1';
    widthInput.value = String(block.data.width);
    widthField.append(widthHeader, widthInput);

    const renderLocalPreview = () => {
        const source = getImageSource(block.data.file_id);
        uploadButton.textContent =
            block.data.file_id == null ? 'Upload image' : 'Replace image';
        widthValue.value = `${block.data.width}%`;

        if (!source) {
            preview.replaceChildren(createPlaceholder());
            return;
        }

        const image = document.createElement('img');
        image.src = source;
        image.alt = block.data.caption;
        image.style.width = `${block.data.width}%`;
        preview.replaceChildren(image);
    };

    uploadButton.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', async () => {
        const [file] = fileInput.files;
        if (!file) {
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        const token = localStorage.getItem(TOKEN_KEY);

        uploadButton.disabled = true;
        uploadButton.textContent = 'Uploading...';
        status.classList.remove('is-error');
        status.textContent = '';

        try {
            const headers = token
                ? { Authorization: `Bearer ${token}` }
                : {};
            const response = await fetch(UPLOAD_ENDPOINT, {
                method: 'POST',
                headers,
                body: formData,
            });

            if (!response.ok) {
                throw new Error(await getErrorMessage(response));
            }

            const uploadedFile = await response.json();
            const imageSource =
                uploadedFile.url ||
                getUploadedImageUrl(uploadedFile.storage_path);
            if (uploadedFile.id == null || !imageSource) {
                throw new Error('The upload response did not include image data.');
            }
            registerImageSource(uploadedFile.id, imageSource);

            block.data.file_id = uploadedFile.id;
            onChange({ file_id: uploadedFile.id });
            renderLocalPreview();
            status.textContent = 'Image uploaded.';
        } catch (error) {
            status.classList.add('is-error');
            status.textContent = error.message || 'Image upload failed.';
            renderLocalPreview();
        } finally {
            uploadButton.disabled = false;
            fileInput.value = '';
        }
    });

    captionInput.addEventListener('input', () => {
        block.data.caption = captionInput.value;
        preview.querySelector('img')?.setAttribute('alt', captionInput.value);
        onChange({ caption: captionInput.value });
    });

    widthInput.addEventListener('input', () => {
        const width = clampWidth(widthInput.value);
        block.data.width = width;
        widthValue.value = `${width}%`;
        const image = preview.querySelector('img');
        if (image) {
            image.style.width = `${width}%`;
        }
        onChange({ width });
    });

    renderLocalPreview();
    editor.append(
        preview,
        fileInput,
        uploadButton,
        status,
        captionField,
        widthField
    );
    return editor;
};
