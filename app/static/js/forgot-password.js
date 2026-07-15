const form = document.querySelector("#forgot-password-form");
const email = form.querySelector("#email");
const message = document.querySelector("#form-message");

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

    if (!email.value.trim()) {
        showError("Введите email.");
        email.focus();
        return;
    }

    if (!email.validity.valid) {
        showError("Введите корректный адрес электронной почты.");
        email.focus();
        return;
    }

    // TODO: Connect password recovery when backend integration is implemented.
});
