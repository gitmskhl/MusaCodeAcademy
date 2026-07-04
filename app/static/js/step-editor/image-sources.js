const imageSources = new Map();

export const registerImageSource = (fileId, source) => {
    if (fileId == null || !source) {
        return;
    }

    imageSources.set(String(fileId), source);
};

export const getImageSource = (fileId) => {
    if (fileId == null) {
        return '';
    }

    return imageSources.get(String(fileId)) ?? '';
};

export const getUploadedImageUrl = (storagePath) => {
    if (!storagePath) {
        return '';
    }

    const encodedPath = storagePath
        .split('/')
        .map((part) => encodeURIComponent(part))
        .join('/');

    return `/uploads/${encodedPath}`;
};
