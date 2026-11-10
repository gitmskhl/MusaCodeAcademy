// Apply the saved theme before the browser paints any page content.
(() => {
    const storageKey = 'musa_code_academy_theme';
    const root = document.documentElement;
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
    const normalize = (value) => ['light', 'dark', 'system'].includes(value) ? value : 'system';
    let preference = 'system';

    try {
        preference = normalize(localStorage.getItem(storageKey));
    } catch {
        // The theme still works when browser storage is unavailable.
    }

    const apply = () => {
        const theme = preference === 'system' ? (systemTheme.matches ? 'dark' : 'light') : preference;
        root.dataset.theme = theme;
        document.querySelectorAll('[data-theme-picker]').forEach((picker) => {
            picker.value = preference;
        });
        document.querySelectorAll('meta[name="theme-color"]').forEach((meta) => {
            meta.content = theme === 'dark' ? '#171c16' : '#f7f8f2';
        });
        document.querySelectorAll('meta[name="color-scheme"]').forEach((meta) => {
            meta.content = theme;
        });
        window.dispatchEvent(new CustomEvent('academy:theme-change', { detail: { theme, preference } }));
    };

    apply();
    document.addEventListener('DOMContentLoaded', apply, { once: true });
    document.addEventListener('change', (event) => {
        if (!event.target.matches('[data-theme-picker]')) return;
        preference = normalize(event.target.value);
        try {
            localStorage.setItem(storageKey, preference);
        } catch {
            // Keep the selection for this page even if it cannot be saved.
        }
        apply();
    });
    systemTheme.addEventListener('change', () => {
        if (preference === 'system') apply();
    });
    window.addEventListener('storage', (event) => {
        if (event.key === storageKey || event.key === null) {
            preference = normalize(event.newValue);
            apply();
        }
    });
})();
