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
        showError("Email is required.");
        email.focus();
        return;
    }

    if (!email.validity.valid) {
        showError("Enter a valid email address.");
        email.focus();
        return;
    }

    // TODO: Connect password recovery when backend integration is implemented.
});
