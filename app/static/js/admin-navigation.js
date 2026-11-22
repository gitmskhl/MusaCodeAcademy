const TOKEN_KEY = 'musa_code_academy_token';

export function setAdminNavigation(user) {
    document.querySelectorAll('[data-admin-link]').forEach(link => {
        link.hidden = user?.role !== 'admin';
    });
}

export function initAdminNavigation() {
    let version = 0;
    async function refresh() {
        const request = ++version;
        setAdminNavigation(null);
        try {
            const token = localStorage.getItem(TOKEN_KEY);
            if (!token) return;
            const response = await fetch('/api/users/me', { headers: { Authorization: `Bearer ${token}` } });
            const user = response.ok ? await response.json() : null;
            if (version === request && localStorage.getItem(TOKEN_KEY) === token) setAdminNavigation(user);
        } catch {
            // A failed role check leaves the administrator link hidden.
        }
    }
    window.addEventListener('storage', event => {
        if (event.key === TOKEN_KEY || event.key === null) void refresh();
    });
    window.addEventListener('pageshow', event => {
        if (event.persisted) void refresh();
    });
    void refresh();
}
