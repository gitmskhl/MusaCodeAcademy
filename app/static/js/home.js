const runButton = document.querySelector('[data-run-demo]');
const output = document.querySelector('[data-demo-output]');

runButton?.addEventListener('click', () => {
    // Preview one iteration of the illustrative Python loop; no user code is executed.
    output.textContent = '› Я могу больше!';
    output.classList.add('is-success');
    runButton.textContent = '✓ Ещё раз';
});

const TOKEN_KEY = 'musa_code_academy_token';
const startLinks = [...document.querySelectorAll('[data-home-start]')].map((link) => ({
    link,
    href: link.getAttribute('href'),
    content: [...link.childNodes].map((node) => node.cloneNode(true)),
}));
const guestLinks = document.querySelectorAll('[data-home-guest]');
const accountLink = document.querySelector('[data-home-account]');

const showAuthenticatedActions = (authenticated) => {
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
            showAuthenticatedActions(true);
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
