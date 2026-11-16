export function safeNextUrl(value) {
    if (!value?.startsWith('/') || value.startsWith('//') || /[\\\u0000-\u0020\u007f]/.test(value)) return '/dashboard';
    try {
        const url = new URL(value, window.location.origin);
        return url.origin === window.location.origin ? `${url.pathname}${url.search}${url.hash}` : '/dashboard';
    } catch { return '/dashboard'; }
}
