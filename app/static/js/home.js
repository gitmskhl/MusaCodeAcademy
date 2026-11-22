import { setAdminNavigation } from './admin-navigation.js';

// Broken uploaded covers reveal the neutral code icon already in the card.
document.querySelectorAll('[data-course-image]').forEach((image) => {
    image.addEventListener('error', () => image.remove(), { once: true });
    if (image.complete && image.naturalWidth === 0) image.remove();
});

const TOKEN_KEY = 'musa_code_academy_token';
const startLinks = [...document.querySelectorAll('[data-home-start]')].map((link) => ({
    link,
    href: link.getAttribute('href'),
    content: [...link.childNodes].map((node) => node.cloneNode(true)),
}));
const guestLinks = document.querySelectorAll('[data-home-guest]');
const accountLink = document.querySelector('[data-home-account]');

const showAuthenticatedActions = (authenticated, user = null) => {
    setAdminNavigation(user);
    startLinks.forEach(({ link, href, content }) => {
        link.href = authenticated ? '/dashboard' : href;
        if (authenticated) {
            const icon = content.find((node) => node.nodeType === Node.ELEMENT_NODE && node.hasAttribute('aria-hidden'));
            link.replaceChildren('Продолжить обучение', ...(icon ? [' ', icon.cloneNode(true)] : []));
        } else {
            link.replaceChildren(...content.map((node) => node.cloneNode(true)));
        }
    });
    guestLinks.forEach((link) => { link.hidden = authenticated; });
    if (accountLink) {
        accountLink.href = authenticated ? '/dashboard' : '/login';
        accountLink.textContent = authenticated ? 'Личный кабинет' : 'Войти';
    }
};

const refreshHomeAuth = async () => {
    setAdminNavigation(null);
    try {
        const token = localStorage.getItem(TOKEN_KEY);
        if (!token) {
            showAuthenticatedActions(false);
            return;
        }
        // The public home page must stay accessible when a session has expired.
        const response = await fetch('/api/users/me', {
            headers: { Authorization: `Bearer ${token}` },
        });
        if (localStorage.getItem(TOKEN_KEY) !== token) return;
        if (response.ok) {
            const user = await response.json();
            if (localStorage.getItem(TOKEN_KEY) !== token) return;
            showAuthenticatedActions(true, user);
        } else if (response.status === 401) {
            localStorage.removeItem(TOKEN_KEY);
            showAuthenticatedActions(false);
        }
    } catch {
        // Keep the page usable if session verification or browser storage fails.
    }
};

window.addEventListener('storage', (event) => {
    if (event.key === TOKEN_KEY || event.key === null) refreshHomeAuth();
});
window.addEventListener('pageshow', (event) => {
    if (event.persisted) refreshHomeAuth();
});
refreshHomeAuth();
