const KINESCOPE_HOST = 'kinescope.io';
const KINESCOPE_EMBED_PATH = '/embed/';

const aspectRatioValues = new Map([
    ['16:9', '16 / 9'],
    ['4:3', '4 / 3'],
    ['1:1', '1 / 1'],
    ['9:16', '9 / 16'],
]);

export const normalizeVideoAspectRatio = (value) =>
    aspectRatioValues.has(value) ? value : '16:9';

export const getVideoAspectRatioValue = (value) =>
    aspectRatioValues.get(normalizeVideoAspectRatio(value));

export const normalizeKinescopeEmbedUrl = (value) => {
    const raw = String(value ?? '').trim();
    if (!raw) {
        return '';
    }

    let source = raw;
    if (raw.toLowerCase().includes('<iframe')) {
        const documentFragment = new DOMParser().parseFromString(
            raw,
            'text/html'
        );
        source =
            documentFragment
                .querySelector('iframe[src]')
                ?.getAttribute('src')
                ?.trim() ?? '';
    }

    try {
        const url = new URL(source);
        const embedId = url.pathname.startsWith(KINESCOPE_EMBED_PATH)
            ? url.pathname.slice(KINESCOPE_EMBED_PATH.length).replaceAll('/', '')
            : '';
        if (
            url.protocol !== 'https:' ||
            url.hostname !== KINESCOPE_HOST ||
            url.port ||
            !embedId
        ) {
            return '';
        }

        return `https://${KINESCOPE_HOST}${url.pathname}${url.search}`;
    } catch {
        return '';
    }
};

const createPlaceholder = () => {
    const placeholder = document.createElement('div');
    placeholder.className =
        'rendered-block__placeholder rendered-video__placeholder';

    const icon = document.createElement('span');
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = 'video';

    const message = document.createElement('p');
    message.textContent = 'No video attached';

    placeholder.append(icon, message);
    return placeholder;
};

export const renderVideoBlock = (block) => {
    const figure = document.createElement('figure');
    figure.className = 'rendered-video';

    const embedUrl = normalizeKinescopeEmbedUrl(block.data.embed_url);
    if (!embedUrl) {
        figure.appendChild(createPlaceholder());
        return figure;
    }

    const frame = document.createElement('div');
    frame.className = 'rendered-video__frame';
    frame.style.setProperty(
        '--video-aspect-ratio',
        getVideoAspectRatioValue(block.data.aspect_ratio)
    );

    const iframe = document.createElement('iframe');
    iframe.src = embedUrl;
    iframe.title = block.data.title?.trim() || 'Kinescope video';
    iframe.allow =
        'autoplay; fullscreen; picture-in-picture; encrypted-media; gyroscope; accelerometer; clipboard-write; screen-wake-lock';
    iframe.allowFullscreen = true;
    iframe.loading = 'lazy';
    iframe.referrerPolicy = 'strict-origin-when-cross-origin';

    frame.appendChild(iframe);
    figure.appendChild(frame);

    if (block.data.caption?.trim()) {
        const caption = document.createElement('figcaption');
        caption.textContent = block.data.caption.trim();
        figure.appendChild(caption);
    }

    return figure;
};
