const form = document.querySelector("#forgot-password-form");
const email = form.querySelector("#email");
const button = form.querySelector("button");
const message = document.querySelector("#form-message");
const successState = document.querySelector("#success-state");
const defaultButtonText = button.textContent;

function showError(text) {
    message.textContent = text;
    message.className = "message is-visible is-error";
}

function clearMessage() {
    message.textContent = "";
    message.className = "message";
}

form.addEventListener("submit", async (event) => {
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

    button.disabled = true;
    button.textContent = "Отправка…";

    try {
        const response = await fetch("/api/auth/forgot-password", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email: email.value.trim()
            })
        });

        if (response.status !== 200) {
            throw new Error("Password reset request failed");
        }

        form.hidden = true;
        clearMessage();
        successState.hidden = false;
        successState.querySelector("h2").focus();
    } catch (error) {
        showError("Не удалось отправить запрос. Попробуйте еще раз позже.");
    } finally {
        button.disabled = false;
        button.textContent = defaultButtonText;
    }
});
