import { normalizeKinescopeEmbedUrl, renderVideoBlock } from './step-renderer/block-renderers/video-renderer.js';

export const initCourseVideo = () => {
    const preview = document.querySelector('[data-course-video]');
    const previewFrame = document.querySelector('[data-course-video-preview]');
    const openButton = document.querySelector('[data-course-video-open]');
    const dialog = document.querySelector('[data-course-video-dialog]');
    const player = document.querySelector('[data-course-video-player]');
    const title = document.querySelector('[data-course-video-title]');
    if (!preview || !previewFrame || !openButton || !dialog || !player) return () => {};

    let videoUrl = '';
    let videoTitle = '';
    let previousOverflow = '';
    const createVideo = () => renderVideoBlock({ data: { embed_url: videoUrl, title: videoTitle } });

    openButton.addEventListener('click', () => {
        if (!videoUrl || dialog.open) return;
        title.textContent = videoTitle;
        player.replaceChildren(createVideo());
        previousOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        dialog.showModal();
    });
    dialog.querySelector('[data-course-video-close]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', (event) => {
        const bounds = dialog.getBoundingClientRect();
        if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right ||
            event.clientY < bounds.top || event.clientY > bounds.bottom)) dialog.close();
    });
    dialog.addEventListener('close', () => {
        player.replaceChildren();
        document.body.style.overflow = previousOverflow;
        openButton.focus();
    });

    return (course) => {
        if (dialog.open) dialog.close();
        videoUrl = normalizeKinescopeEmbedUrl(course?.promo_video_url);
        videoTitle = course?.title ? `Видео о курсе «${course.title}»` : 'Видео о курсе';
        preview.hidden = !videoUrl;
        previewFrame.replaceChildren();
        if (videoUrl) {
            const video = createVideo();
            const iframe = video.querySelector('iframe');
            iframe.tabIndex = -1;
            iframe.setAttribute('aria-hidden', 'true');
            previewFrame.append(video);
        }
    };
};
