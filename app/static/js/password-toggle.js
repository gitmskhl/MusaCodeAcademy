document.querySelectorAll('[data-password-toggle]').forEach((button) => {
    const input = document.getElementById(button.getAttribute('aria-controls'));
    const fieldName = input.id === 'password_confirm' ? 'повтор пароля' : 'пароль';

    button.addEventListener('click', () => {
        const isVisible = input.type === 'password';
        input.type = isVisible ? 'text' : 'password';
        button.setAttribute('aria-pressed', String(isVisible));
        button.setAttribute('aria-label', `${isVisible ? 'Скрыть' : 'Показать'} ${fieldName}`);
    });
});
