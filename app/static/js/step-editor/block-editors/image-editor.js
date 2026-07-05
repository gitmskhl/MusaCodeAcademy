import {
    getImageWidth,
    renderImageBlock,
} from '../block-renderers/image-renderer.js';
import {
    getImageSource,
    getUploadedImageUrl,
    registerImageSource,
} from '../image-sources.js';

const UPLOAD_ENDPOINT = '/api/files/images';
const TOKEN_KEY = 'musa_code_academy_token';

const roundWidth = (width) => Math.round(width * 10) / 10;

const addResizeControls = ({ figure, block, onChange }) => {
    const image = figure.querySelector('img');
    if (!image) {
        return;
    }

    const frame = document.createElement('div');
    frame.className = 'image-resize-frame';
    image.replaceWith(frame);
    frame.appendChild(image);

    const setWidth = (width) => {
        const nextWidth = roundWidth(getImageWidth(width));
        if (nextWidth === getImageWidth(block.data.width)) {
            return;
        }

        figure.style.width = `${nextWidth}%`;
        onChange({ width: nextWidth });
        frame.querySelectorAll('[data-image-resize-handle]').forEach((handle) => {
            handle.setAttribute('aria-label', `Resize image, currently ${nextWidth}%`);
        });
    };

    ['left', 'right'].forEach((side) => {
        const handle = document.createElement('button');
        handle.className =
            `image-resize-handle image-resize-handle--${side}`;
        handle.type = 'button';
        handle.dataset.imageResizeHandle = side;
        handle.setAttribute(
            'aria-label',
            `Resize image, currently ${getImageWidth(block.data.width)}%`
        );
        handle.title = 'Drag to resize';

        handle.addEventListener('pointerdown', (event) => {
            if (event.pointerType === 'mouse' && event.button !== 0) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();

            const containerWidth = figure.parentElement?.clientWidth ?? 0;
            if (!containerWidth) {
                return;
            }

            const startX = event.clientX;
            const startWidth = getImageWidth(block.data.width);
            const direction = side === 'right' ? 1 : -1;
            handle.setPointerCapture(event.pointerId);
            figure.classList.add('is-resizing');

            const resize = (moveEvent) => {
                if (moveEvent.pointerId !== event.pointerId) {
                    return;
                }
                const delta =
                    ((moveEvent.clientX - startX) / containerWidth) * 200;
                setWidth(startWidth + direction * delta);
            };

            const finish = (endEvent) => {
                if (endEvent.pointerId !== event.pointerId) {
                    return;
                }
                figure.classList.remove('is-resizing');
                handle.removeEventListener('pointermove', resize);
                handle.removeEventListener('pointerup', finish);
                handle.removeEventListener('pointercancel', finish);
            };

            handle.addEventListener('pointermove', resize);
            handle.addEventListener('pointerup', finish);
            handle.addEventListener('pointercancel', finish);
        });

        handle.addEventListener('keydown', (event) => {
            const direction = side === 'right' ? 1 : -1;
            const increment = event.shiftKey ? 5 : 1;
            let nextWidth;

            if (event.key === 'ArrowLeft') {
                nextWidth = getImageWidth(block.data.width) -
                    direction * increment;
            } else if (event.key === 'ArrowRight') {
                nextWidth = getImageWidth(block.data.width) +
                    direction * increment;
            } else if (event.key === 'Home') {
                nextWidth = 20;
            } else if (event.key === 'End') {
                nextWidth = 100;
            } else {
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            setWidth(nextWidth);
        });

        frame.appendChild(handle);
    });
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
    block.data.caption = block.data.caption ?? '';
    const editor = document.createElement('div');
    editor.className = 'inline-image-editor';
    const figure = renderImageBlock(block);
    editor.appendChild(figure);

    const source = getImageSource(block.data.file_id);
    if (source) {
        addResizeControls({ figure, block, onChange });
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
