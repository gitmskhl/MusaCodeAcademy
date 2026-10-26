import { logout } from './course-auth.js';

const profileMenus = document.querySelectorAll('[data-app-profile]');
const logoutButtons = document.querySelectorAll('[data-app-logout]');

const closeMenu = (menu) => {
    const button = menu.querySelector('[data-app-profile-button]');

    menu.classList.remove('is-open');
    button?.setAttribute('aria-expanded', 'false');
};

const closeOtherMenus = (activeMenu) => {
    profileMenus.forEach((menu) => {
        if (menu !== activeMenu) {
            closeMenu(menu);
        }
    });
};

profileMenus.forEach((menu) => {
    const button = menu.querySelector('[data-app-profile-button]');

    menu.addEventListener('focusout', (event) => {
        if (!menu.contains(event.relatedTarget)) closeMenu(menu);
    });
    menu.addEventListener('keydown', (event) => {
        const items = [...menu.querySelectorAll('[role="menuitem"]')];
        if (event.key === 'Escape') {
            closeMenu(menu);
            button.focus();
            return;
        }
        if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        menu.classList.add('is-open');
        button.setAttribute('aria-expanded', 'true');
        const index = items.indexOf(document.activeElement);
        let next = event.key === 'ArrowUp' ? (index - 1 + items.length) % items.length : (index + 1) % items.length;
        if (index === -1) next = event.key === 'ArrowUp' ? items.length - 1 : 0;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = items.length - 1;
        items[next]?.focus();
    });
    button?.addEventListener('click', () => {
        const isOpen = menu.classList.toggle('is-open');

        button.setAttribute('aria-expanded', String(isOpen));
        if (isOpen) {
            closeOtherMenus(menu);
        }
    });
});

logoutButtons.forEach((button) => {
    button.addEventListener('click', logout);
});

document.addEventListener('click', (event) => {
    profileMenus.forEach((menu) => {
        if (!menu.contains(event.target)) {
            closeMenu(menu);
        }
    });
});

document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') {
        return;
    }

    profileMenus.forEach(closeMenu);
});
