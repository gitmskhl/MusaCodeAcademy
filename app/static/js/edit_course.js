(function () {
    const TOKEN_KEY = 'musa_code_academy_token';

    const state = {
        loading: null,
        error: null,
        content: null,
        form: null,
        messageBox: null,
        progressBar: null,
    };

    const slugify = (value) =>
        value
            .toLowerCase()
            .trim()
            .replace(/[^a-z0-9\s-]/g, '')
            .replace(/\s+/g, '-')
            .replace(/-+/g, '-')
            .replace(/^-+|-+$/g, '');

    const getToken = () => localStorage.getItem(TOKEN_KEY);

    const clearToken = () => localStorage.removeItem(TOKEN_KEY);

    const redirectHome = () => {
        window.location.href = '/';
    };

    const showLoading = (message = 'Проверка доступа...') => {
        if (!state.loading) return;

        state.loading.hidden = false;
        state.loading.textContent = message;
    };

    const hideLoading = () => {
        if (!state.loading) return;

        state.loading.hidden = true;
    };

    const showError = (message) => {
        if (!state.error) return;

        state.error.hidden = false;
        state.error.textContent = message;
    };

    const hideError = () => {
        if (!state.error) return;

        state.error.hidden = true;
        state.error.textContent = '';
    };

    const showContent = () => {
        if (!state.content) return;

        state.content.hidden = false;
    };

    const hideContent = () => {
        if (!state.content) return;

        state.content.hidden = true;
    };

    const getMessageBox = (form) => form.querySelector('#course-form-message');

    const getProgressBar = (form) => form.querySelector('[data-form-progress]');

    const getSubmitButton = (form) => form.querySelector('[data-course-submit]');

    const setFormMessage = (box, kind, text) => {
        if (!box) return;

        box.className = `form-message is-visible ${kind}`;
        box.textContent = text;
    };

    const clearFormMessage = (box) => {
        if (!box) return;

        box.className = 'form-message';
        box.textContent = '';
    };

    const setFormBusy = (form, isBusy) => {
        const submitButton = getSubmitButton(form);
        const progressBar = getProgressBar(form);

        form.setAttribute('aria-busy', String(isBusy));

        if (submitButton) {
            submitButton.disabled = isBusy;
            submitButton.textContent = isBusy ? 'Сохранение...' : 'Сохранить';
        }

        if (progressBar) {
            progressBar.hidden = !isBusy;
            progressBar.classList.toggle('is-active', isBusy);
        }
    };

    const setFieldError = (form, fieldName, message) => {
        const input = form.querySelector(`[name="${fieldName}"]`);
        const error = form.querySelector(`[data-error-for="${fieldName}"]`);

        if (input) {
            input.setAttribute('aria-invalid', 'true');
        }

        if (error) {
            error.textContent = message;
        }
    };

    const clearFieldError = (form, fieldName) => {
        const input = form.querySelector(`[name="${fieldName}"]`);
        const error = form.querySelector(`[data-error-for="${fieldName}"]`);

        if (input) {
            input.removeAttribute('aria-invalid');
        }

        if (error) {
            error.textContent = '';
        }
    };

    const getBackendErrorMessage = async (response, fallbackMessage) => {
        const responseCopy = response.clone();

        try {
            const data = await response.json();
            return data?.detail || data?.message || fallbackMessage;
        } catch (jsonError) {
            try {
                const text = await responseCopy.text();
                return text || fallbackMessage;
            } catch (textError) {
                return fallbackMessage;
            }
        }
    };

    const validateCourseForm = (form) => {
        const title = form.querySelector('#course-title');
        const shortDescription = form.querySelector('#course-short-description');
        const description = form.querySelector('#course-description');
        const slug = form.querySelector('#course-slug');

        clearFieldError(form, 'title');
        clearFieldError(form, 'short_description');
        clearFieldError(form, 'description');
        clearFieldError(form, 'slug');

        const values = {
            title: title ? title.value.trim() : '',
            short_description: shortDescription ? shortDescription.value.trim() : '',
            description: description ? description.value.trim() : '',
            slug: slug ? slug.value.trim() : '',
        };

        let firstInvalid = null;

        if (!values.title) {
            setFieldError(form, 'title', 'Название курса обязательно.');
            firstInvalid = firstInvalid || title;
        } else if (values.title.length < 5) {
            setFieldError(form, 'title', 'Название курса должно содержать минимум 5 символов.');
            firstInvalid = firstInvalid || title;
        }

        if (!values.short_description) {
            setFieldError(form, 'short_description', 'Краткое описание обязательно.');
            firstInvalid = firstInvalid || shortDescription;
        } else if (values.short_description.length < 10) {
            setFieldError(
                form,
                'short_description',
                'Краткое описание должно содержать минимум 10 символов.'
            );
            firstInvalid = firstInvalid || shortDescription;
        }

        if (!values.description) {
            setFieldError(form, 'description', 'Описание курса обязательно.');
            firstInvalid = firstInvalid || description;
        } else if (values.description.length < 20) {
            setFieldError(form, 'description', 'Описание курса должно содержать минимум 20 символов.');
            firstInvalid = firstInvalid || description;
        }

        if (!values.slug) {
            setFieldError(form, 'slug', 'Slug обязателен.');
            firstInvalid = firstInvalid || slug;
        } else if (values.slug.length < 2) {
            setFieldError(form, 'slug', 'Slug должен содержать минимум 2 символа.');
            firstInvalid = firstInvalid || slug;
        } else if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(values.slug)) {
            setFieldError(form, 'slug', 'Используйте строчные буквы, цифры и дефисы.');
            firstInvalid = firstInvalid || slug;
        }

        return {
            valid: !firstInvalid,
            firstInvalid,
        };
    };

    const checkAdminAccess = async () => {
        const token = getToken();
        if (!token) {
            redirectHome();
            return null;
        }

        const response = await fetch('/api/users/me', {
            method: 'GET',
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });

        if (response.status === 401) {
            clearToken();
            redirectHome();
            return null;
        }

        if (!response.ok) {
            redirectHome();
            return null;
        }

        const user = await response.json();
        if (user.role !== 'admin') {
            redirectHome();
            return null;
        }

        return { token, user };
    };

    const loadCourse = async (courseId) => {
        const token = getToken();

        if (!token) {
            redirectHome();
            return null;
        }

        showLoading('Загрузка курса...');

        const response = await fetch(`/api/courses/${courseId}/admin`, {
            method: 'GET',
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });

        if (response.status === 401) {
            clearToken();
            redirectHome();
            return null;
        }

        if (!response.ok) {
            const message = await getBackendErrorMessage(response, 'Не удалось загрузить курс.');
            throw new Error(message || 'Не удалось загрузить курс.');
        }

        return response.json();
    };

    const populateForm = (form, course) => {
        const title = form.querySelector('#course-title');
        const slug = form.querySelector('#course-slug');
        const shortDescription = form.querySelector('#course-short-description');
        const description = form.querySelector('#course-description');
        const isPublished = form.querySelector('#course-is-published');

        if (title) {
            title.value = course.title ?? '';
        }

        if (slug) {
            slug.value = course.slug ?? '';
        }

        if (shortDescription) {
            shortDescription.value = course.short_description ?? '';
        }

        if (description) {
            description.value = course.description ?? '';
        }

        if (isPublished) {
            isPublished.value = course.is_published ? 'true' : 'false';
        }
    };

    const initEditCourseForm = async () => {
        const form = document.querySelector('[data-course-edit-form]');

        if (!form) {
            return;
        }

        const main = document.querySelector('[data-admin-content]');
        const courseId = main?.dataset.courseId;

        state.form = form;
        state.messageBox = getMessageBox(form);
        state.progressBar = getProgressBar(form);

        const title = form.querySelector('#course-title');
        const shortDescription = form.querySelector('#course-short-description');
        const description = form.querySelector('#course-description');
        const slug = form.querySelector('#course-slug');
        const isPublished = form.querySelector('#course-is-published');
        const messageBox = state.messageBox;
        let slugTouched = Boolean(slug && slug.value.trim());
        let isSubmitting = false;

        if (state.progressBar) {
            state.progressBar.hidden = true;
        }

        if (!courseId) {
            hideLoading();
            showError('Не удалось определить курс для редактирования.');
            return;
        }

        if (title && slug) {
            title.addEventListener('input', () => {
                if (!slugTouched) {
                    slug.value = slugify(title.value);
                }
                clearFieldError(form, 'title');
                clearFormMessage(messageBox);
            });

            if (shortDescription) {
                shortDescription.addEventListener('input', () => {
                    clearFieldError(form, 'short_description');
                    clearFormMessage(messageBox);
                });
            }

            if (description) {
                description.addEventListener('input', () => {
                    clearFieldError(form, 'description');
                    clearFormMessage(messageBox);
                });
            }

            slug.addEventListener('input', () => {
                slugTouched = Boolean(slug.value.trim());
                clearFieldError(form, 'slug');
                clearFormMessage(messageBox);
            });
        }

        ['title', 'short_description', 'description', 'slug', 'is_published'].forEach((fieldName) => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (!field) return;

            field.addEventListener('input', () => {
                clearFieldError(form, fieldName);
            });

            if (fieldName === 'is_published') {
                field.addEventListener('change', () => {
                    clearFieldError(form, fieldName);
                    clearFormMessage(messageBox);
                });
            }
        });

        try {
            const access = await checkAdminAccess();

            if (!access) {
                return;
            }

            const course = await loadCourse(courseId);

            if (!course) {
                return;
            }

            populateForm(form, course);
            hideLoading();
            showContent();

            form.addEventListener('submit', async (event) => {
                event.preventDefault();

                if (isSubmitting) {
                    return;
                }

                clearFormMessage(messageBox);

                const result = validateCourseForm(form);

                if (!result.valid) {
                    setFormMessage(messageBox, 'is-error', 'Проверьте выделенные поля.');
                    if (result.firstInvalid) {
                        result.firstInvalid.focus();
                    }
                    return;
                }

                const token = getToken();

                if (!token) {
                    setFormMessage(messageBox, 'is-error', 'Не удалось найти токен доступа. Войдите заново.');
                    return;
                }

                const payload = {
                    title: title ? title.value.trim() : '',
                    slug: slug ? slug.value.trim() : '',
                    short_description: shortDescription ? shortDescription.value.trim() : '',
                    description: description ? description.value.trim() : '',
                    is_published: isPublished ? isPublished.value === 'true' : false,
                };

                isSubmitting = true;
                setFormBusy(form, true);
                try {
                    const response = await fetch(`/api/courses/${courseId}`, {
                        method: 'PATCH',
                        headers: {
                            Authorization: `Bearer ${token}`,
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(payload),
                    });

                    if (response.status === 401) {
                        clearToken();
                        redirectHome();
                        return;
                    }

                    if (!response.ok) {
                        const errorMessage = await getBackendErrorMessage(
                            response,
                            'Не удалось сохранить курс. Попробуйте еще раз.'
                        );

                        throw new Error(errorMessage || 'Не удалось сохранить курс. Попробуйте еще раз.');
                    }

                    window.location.href = '/admin';
                } catch (error) {
                    setFormMessage(
                        messageBox,
                        'is-error',
                        error instanceof Error && error.message
                            ? error.message
                            : 'Не удалось сохранить курс. Попробуйте еще раз.'
                    );
                } finally {
                    isSubmitting = false;
                    setFormBusy(form, false);
                }
            });
        } catch (error) {
            hideLoading();
            showError(
                error instanceof Error && error.message
                    ? error.message
                    : 'Не удалось загрузить курс.'
            );
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        state.loading = document.querySelector('[data-admin-loading]');
        state.error = document.querySelector('[data-admin-error]');
        state.content = document.querySelector('[data-admin-content]');

        hideError();
        hideContent();
        showLoading();

        initEditCourseForm();
    });
})();
