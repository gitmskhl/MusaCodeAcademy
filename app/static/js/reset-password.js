const form = document.querySelector("#reset-password-form");
const password = form.querySelector("#password");
const passwordConfirm = form.querySelector("#password-confirm");
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

    if (!password.value) {
        showError("Password is required.");
        password.focus();
        return;
    }

    if (!passwordConfirm.value) {
        showError("Please confirm your password.");
        passwordConfirm.focus();
        return;
    }

    if (password.value !== passwordConfirm.value) {
        showError("Passwords do not match.");
        passwordConfirm.focus();
        return;
    }

    // TODO: Save the new password when backend integration is implemented.
});
