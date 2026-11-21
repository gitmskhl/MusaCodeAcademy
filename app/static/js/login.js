import { safeNextUrl } from './safe-next.js';
import { setupAuthForm } from './auth-form.js';

const form = document.querySelector("#login-form");
const button = form.querySelector('button[type="submit"]');
const { clearErrors, showMessage, setSubmitting } = setupAuthForm(form);
const TOKEN_KEY = "musa_code_academy_token";

async function redirectAuthenticatedUser() {
    const token = localStorage.getItem(TOKEN_KEY);

    if (!token) {
        document.documentElement.classList.remove("is-auth-checking");
        return;
    }

    try {
        const response = await fetch("/api/users/me", {
            headers: {
                Authorization: `Bearer ${token}`
            }
        });

        if (response.status === 200) {
            window.location.replace(safeNextUrl(new URLSearchParams(window.location.search).get('next')));
            return;
        }

        if (response.status === 401) {
            localStorage.removeItem(TOKEN_KEY);
        }
    } catch (error) {
        console.error(error);
    }

    document.documentElement.classList.remove("is-auth-checking");
}

const FIELD_LABELS = {
    username: "email",
    password: "пароль"
};

const ERROR_TEXTS = {
    "Incorrect email or password": "Неверный email или пароль."
};

function getFieldLabel(error) {
    const field = error?.loc?.at(-1);
    return FIELD_LABELS[field] || "поле";
}

function getValidationErrorText(error) {
    const fieldLabel = getFieldLabel(error);

    if (error.type === "missing") {
        return `Заполните поле «${fieldLabel}».`;
    }

    if (error.type === "string_too_short") {
        return `Поле «${fieldLabel}» должно содержать минимум ${error.ctx?.min_length || 1} символов.`;
    }

    return error.msg || "Проверьте данные формы.";
}

function getErrorText(detail) {
    if (Array.isArray(detail)) {
        return detail.map(getValidationErrorText).join(" ");
    }

    return ERROR_TEXTS[detail] || detail || "Не удалось выполнить вход. Проверьте данные и попробуйте снова.";
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (button.disabled) return;
    clearErrors();
    setSubmitting(true, "Вход…");

    try {
        const response = await fetch(form.action, {
            method: "POST",
            body: new FormData(form)
        });
        const data = await response.json();

        if (!response.ok) {
            const errors = Array.isArray(data.detail) ? data.detail.map((error) => ({
                name: error.loc?.at(-1), text: getValidationErrorText(error)
            })) : [];
            showMessage(getErrorText(data.detail), "error", errors);
            return;
        }

        localStorage.setItem(TOKEN_KEY, data.access_token);
        const nextUrl = new URLSearchParams(window.location.search).get("next");
        const destination = safeNextUrl(nextUrl);
        window.location.href = destination;
    } catch (error) {
        showMessage(error.message, "error");
    } finally {
        setSubmitting(false);
    }
});

redirectAuthenticatedUser();
