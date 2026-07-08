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
