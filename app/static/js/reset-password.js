const form = document.querySelector("#reset-password-form");
const password = form.querySelector("#password");
const passwordConfirm = form.querySelector("#password-confirm");
const message = document.querySelector("#form-message");
const loadingState = document.querySelector("#loading-state");
const invalidLinkState = document.querySelector("#invalid-link-state");
const invalidLinkMessage = document.querySelector("#invalid-link-message");
const successState = document.querySelector("#success-state");
const loginLink = document.querySelector("#login-link");
const button = form.querySelector("button");
const defaultButtonText = button.textContent;
const token = new URLSearchParams(window.location.search).get("token");
let isSubmitting = false;

const INVALID_LINK_MESSAGE = "Ссылка для сброса пароля недействительна или срок ее действия истек.";
const RESET_ERROR_MESSAGE = "Не удалось изменить пароль. Попробуйте еще раз позже.";

function showForm() {
    loadingState.hidden = true;
    invalidLinkState.hidden = true;
    form.hidden = false;
}

function showInvalidLink(text) {
    loadingState.hidden = true;
    form.hidden = true;
    invalidLinkMessage.textContent = text;
    invalidLinkState.hidden = false;
}

function showSuccess() {
    form.hidden = true;
    message.hidden = true;
    loginLink.hidden = true;
    successState.hidden = false;
    successState.querySelector("h2").focus();
}

async function verifyResetToken() {
    if (!token || !token.trim()) {
        showInvalidLink("Ссылка для сброса пароля недействительна.");
        return;
    }

    try {
        const response = await fetch(
            `/api/auth/reset-password/verify?${new URLSearchParams({ token })}`
        );

        if (!response.ok) {
            throw new Error("Password reset token verification failed");
        }

        showForm();
    } catch (error) {
        showInvalidLink(INVALID_LINK_MESSAGE);
    }
}

function showError(text) {
    message.textContent = text;
    message.className = "message is-visible is-error";
}

function clearMessage() {
    message.textContent = "";
    message.className = "message";
}

async function getErrorText(response) {
    try {
        const data = await response.json();

        if (Array.isArray(data.detail)) {
            return data.detail.map((item) => item.msg).join(" ");
        }

        return data.detail || data.message || RESET_ERROR_MESSAGE;
    } catch (error) {
        return RESET_ERROR_MESSAGE;
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (isSubmitting) {
        return;
    }

    clearMessage();

    if (!password.value) {
        showError("Введите пароль.");
        password.focus();
        return;
    }

    if (!passwordConfirm.value) {
        showError("Подтвердите пароль.");
        passwordConfirm.focus();
        return;
    }

    if (password.value !== passwordConfirm.value) {
        showError("Пароли не совпадают.");
        passwordConfirm.focus();
        return;
    }

    isSubmitting = true;
    button.disabled = true;
    button.textContent = "Изменение…";

    try {
        const response = await fetch("/api/auth/reset-password", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                token,
                new_password: password.value
            })
        });

        if (!response.ok) {
            throw new Error(await getErrorText(response));
        }

        clearMessage();
        showSuccess();
    } catch (error) {
        showError(error.message || RESET_ERROR_MESSAGE);
    } finally {
        isSubmitting = false;
        button.disabled = false;
        button.textContent = defaultButtonText;
    }
});

verifyResetToken();
