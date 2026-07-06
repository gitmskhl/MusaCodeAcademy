const form = document.querySelector("#register-form");
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

    return detail || "Не удалось создать аккаунт. Проверьте данные и попробуйте снова.";
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (form.password.value !== form.password_confirm.value) {
        showMessage("Пароли не совпадают.", "error");
        return;
    }

    button.disabled = true;

    const payload = {
        first_name: form.first_name.value.trim(),
        last_name: form.last_name.value.trim(),
        email: form.email.value.trim(),
        password: form.password.value
    };

    try {
        const response = await fetch(form.action, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(getErrorText(data.detail));
        }

        localStorage.setItem("musa_code_academy_token", data.token.access_token);
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
