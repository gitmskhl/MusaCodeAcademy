const form = document.querySelector("#reset-password-form");
const password = form.querySelector("#password");
const passwordConfirm = form.querySelector("#password-confirm");
const message = document.querySelector("#form-message");
const loadingState = document.querySelector("#loading-state");
const invalidLinkState = document.querySelector("#invalid-link-state");
const invalidLinkMessage = document.querySelector("#invalid-link-message");

const INVALID_LINK_MESSAGE = "Ссылка для сброса пароля недействительна или срок ее действия истек.";

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

async function verifyResetToken() {
    const token = new URLSearchParams(window.location.search).get("token");

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

form.addEventListener("submit", (event) => {
    event.preventDefault();
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

    // TODO: Save the new password when backend integration is implemented.
});

verifyResetToken();
