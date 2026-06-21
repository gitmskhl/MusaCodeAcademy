const form = document.querySelector("#login-form");
const message = document.querySelector("#form-message");
const button = form.querySelector("button");

function showMessage(text, type) {
    message.textContent = text;
    message.className = `message is-visible is-${type}`;
}

function getErrorText(detail) {
    if (Array.isArray(detail)) {
        return detail.map((item) => item.msg).join(" ");
    }

    return detail || "Не удалось выполнить вход. Проверьте данные и попробуйте снова.";
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

        localStorage.setItem("musa_code_academy_token", data.access_token);
        showMessage("Вход выполнен. Данные авторизации сохранены.", "success");
        form.reset();
    } catch (error) {
        showMessage(error.message, "error");
    } finally {
        button.disabled = false;
    }
});