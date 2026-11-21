// Presentation shared by login and registration; request payloads stay in each page module.
export function setupAuthForm(form) {
    const message = document.querySelector('#form-message');
    const button = form.querySelector('button[type="submit"]');
    const buttonText = button.textContent;
    const fieldErrors = new Map();

    function clearFieldError(input) {
        const state = fieldErrors.get(input);
        if (!state) return;
        state.element.remove();
        input.removeAttribute('aria-invalid');
        if (state.description) input.setAttribute('aria-describedby', state.description);
        else input.removeAttribute('aria-describedby');
        fieldErrors.delete(input);
    }

    function clearMessage() {
        message.textContent = '';
        message.className = 'message mca-alert';
    }

    function clearErrors() {
        clearMessage();
        for (const input of fieldErrors.keys()) clearFieldError(input);
    }

    function showMessage(text, type, errors = []) {
        clearErrors();
        for (const error of errors) {
            const input = form.elements.namedItem(error.name);
            if (!input || fieldErrors.has(input)) continue;
            const element = document.createElement('p');
            element.id = `${input.id}-error`;
            element.className = 'mca-field-error';
            element.textContent = error.text;
            const description = input.getAttribute('aria-describedby');
            input.closest('.mca-field').append(element);
            input.setAttribute('aria-invalid', 'true');
            input.setAttribute('aria-describedby', [description, element.id].filter(Boolean).join(' '));
            fieldErrors.set(input, { element, description });
        }
        message.className = `message mca-alert is-visible is-${type}`;
        message.textContent = text;
        if (type === 'error') {
            const firstInvalid = fieldErrors.keys().next().value;
            (firstInvalid || message).focus();
        }
    }

    function setSubmitting(submitting, label) {
        button.disabled = submitting;
        button.textContent = submitting ? label : buttonText;
        button.setAttribute('aria-busy', String(submitting));
        form.setAttribute('aria-busy', String(submitting));
    }

    form.addEventListener('input', (event) => {
        clearFieldError(event.target);
        clearMessage();
    });

    return { clearErrors, showMessage, setSubmitting };
}
