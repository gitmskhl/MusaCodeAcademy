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
            const label = theme === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему';
            picker.setAttribute('aria-label', label);
            picker.title = label;
        });
        document.querySelectorAll('meta[name="theme-color"]').forEach((meta) => {
            meta.content = theme === 'dark' ? '#151923' : '#fcfdff';
        });
        document.querySelectorAll('meta[name="color-scheme"]').forEach((meta) => {
            meta.content = theme;
        });
        document.querySelectorAll('[data-theme-icon]').forEach((icon) => {
            icon.href = theme === 'dark' ? icon.dataset.darkHref : icon.dataset.lightHref;
        });
        window.dispatchEvent(new CustomEvent('academy:theme-change', { detail: { theme, preference } }));
    };

    apply();
    document.addEventListener('DOMContentLoaded', apply, { once: true });
    document.addEventListener('click', (event) => {
        if (!event.target.closest?.('[data-theme-picker]')) return;
        preference = root.dataset.theme === 'dark' ? 'light' : 'dark';
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
