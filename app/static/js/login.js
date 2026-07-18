const form = document.querySelector("#login-form");
const message = document.querySelector("#form-message");
const button = form.querySelector("button");
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
            window.location.replace("/dashboard");
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

function showMessage(text, type) {
    message.textContent = text;
    message.className = `message is-visible is-${type}`;
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
    button.disabled = true;

    try {
        const response = await fetch(form.action, {
            method: "POST",
            body: new FormData(form)
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(getErrorText(data.detail));
        }

        localStorage.setItem(TOKEN_KEY, data.access_token);
        const nextUrl = new URLSearchParams(window.location.search).get("next");
        const destination = nextUrl?.startsWith("/") && !nextUrl.startsWith("//")
            ? nextUrl
            : "/dashboard";
        window.location.href = destination;
    } catch (error) {
        showMessage(error.message, "error");
    } finally {
        button.disabled = false;
    }
});

redirectAuthenticatedUser();
