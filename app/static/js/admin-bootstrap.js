// Keep this entry independent: failures in the page's module graph must be
// caught before they can leave the access check on screen indefinitely.
export async function bootstrapAdminPage(script, { loadModule = url => import(url), timeoutMs = 20000 } = {}) {
    const loading = document.querySelector('[data-loading], [data-admin-loading]');
    const showFailure = error => {
        if (!loading || loading.hidden) return;
        console.error('Admin page could not start:', error);
        loading.setAttribute('role', 'alert');
        const message = document.createElement('p');
        message.textContent = 'Не удалось загрузить панель администратора. Попробуйте обновить страницу.';
        const retry = document.createElement('button');
        retry.type = 'button';
        retry.className = 'button button--primary';
        retry.textContent = 'Повторить загрузку';
        retry.addEventListener('click', () => window.location.reload());
        loading.replaceChildren(message, retry);
    };
    const timer = setTimeout(() => showFailure(new Error('Admin page startup timed out')), timeoutMs);
    try {
        await loadModule(new URL(script.dataset.adminEntry, script.src).href);
    } catch (error) {
        clearTimeout(timer);
        showFailure(error);
    }
    if (loading?.hidden) clearTimeout(timer);
}

const script = document.querySelector('script[data-admin-entry]');
if (script) void bootstrapAdminPage(script);
