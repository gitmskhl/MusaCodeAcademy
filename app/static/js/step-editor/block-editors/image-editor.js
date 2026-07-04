import { renderImageBlock } from '../block-renderers/image-renderer.js';
import {
    getImageSource,
    getUploadedImageUrl,
    registerImageSource,
} from '../image-sources.js';

const UPLOAD_ENDPOINT = '/api/files/images';
const TOKEN_KEY = 'musa_code_academy_token';

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
    block.data.caption = block.data.caption ?? '';
    const editor = document.createElement('div');
    editor.className = 'inline-image-editor';
    const figure = renderImageBlock(block);
    editor.appendChild(figure);

    const source = getImageSource(block.data.file_id);
    if (source) {
        figure.querySelector('figcaption')?.remove();
        const caption = document.createElement('input');
        caption.className = 'inline-image-editor__caption';
        caption.id = `image-caption-${index}`;
        caption.type = 'text';
        caption.value = block.data.caption;
        caption.placeholder = 'Add a caption…';
        caption.setAttribute('aria-label', 'Image caption');
        caption.dataset.propertiesFirstField = '';
        caption.addEventListener('input', () => {
            figure.querySelector('img')?.setAttribute('alt', caption.value);
            onChange({ caption: caption.value });
        });
        figure.appendChild(caption);
        return editor;
    }

    const fileInput = document.createElement('input');
    fileInput.className = 'inline-image-editor__file-input';
    fileInput.id = `image-file-${index}`;
    fileInput.type = 'file';
    fileInput.accept = 'image/*';

    const uploadButton = document.createElement('button');
    uploadButton.className = 'inline-image-editor__upload';
    uploadButton.type = 'button';
    uploadButton.textContent = 'Upload image';
    uploadButton.dataset.propertiesFirstField = '';

    const status = document.createElement('p');
    status.className = 'inline-image-editor__status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');

    figure.querySelector('.rendered-image__placeholder')?.appendChild(uploadButton);
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
        uploadButton.textContent = 'Uploading…';
        status.classList.remove('is-error');
        status.textContent = '';

        try {
            const headers = token ? { Authorization: `Bearer ${token}` } : {};
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
            onChange({ file_id: uploadedFile.id });
        } catch (error) {
            status.classList.add('is-error');
            status.textContent = error.message || 'Image upload failed.';
            uploadButton.disabled = false;
            uploadButton.textContent = 'Upload image';
            fileInput.value = '';
        }
    });

    editor.append(fileInput, status);
    return editor;
};
