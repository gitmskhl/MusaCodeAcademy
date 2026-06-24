(function () {
    const TOKEN_KEY = 'musa_code_academy_token';

    const state = {
        content: null,
        loading: null,
        error: null,
        courseList: null,
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

    const setStatusBadge = (isPublished) => {
        const label = isPublished ? 'Опубликован' : 'Черновик';
        const modifier = isPublished
            ? 'status-badge status-badge--published'
            : 'status-badge status-badge--draft';

        return {
            label,
            modifier,
        };
    };

    const renderCourses = (courses) => {
        if (!state.courseList) return;

        state.courseList.innerHTML = '';

        if (!Array.isArray(courses) || courses.length === 0) {
            state.courseList.innerHTML = `
                <div class="empty-state" role="status">
                    <p class="empty-state__title">Курсы пока не добавлены.</p>
                    <p class="empty-state__text">Нажмите «Создать курс», чтобы добавить первый курс.</p>
                </div>
            `;
            return;
        }

        const fragment = document.createDocumentFragment();

        courses.forEach((course) => {
            const isPublished = Boolean(course.is_published);
            const badge = setStatusBadge(isPublished);

            const card = document.createElement('article');
            card.className = 'course-card';
            card.setAttribute('role', 'listitem');

            const body = document.createElement('div');
            body.className = 'course-card__body';

            const topline = document.createElement('div');
            topline.className = 'course-card__topline';

            const title = document.createElement('h3');
            title.textContent = course.title ?? 'Без названия';

            const badgeEl = document.createElement('span');
            badgeEl.className = badge.modifier;
            badgeEl.textContent = badge.label;

            topline.append(title, badgeEl);
            body.append(topline);

            const actions = document.createElement('div');
            actions.className = 'course-card__actions';

            const openLink = document.createElement('a');
            openLink.className = 'button button--ghost';
            openLink.href = `/admin/courses/${course.id}`;
            openLink.textContent = 'Открыть';

            const settingsLink = document.createElement('a');
            settingsLink.className = 'button button--ghost';
            settingsLink.href = `/admin/courses/${course.id}#settings`;
            settingsLink.textContent = 'Настройки';

            actions.append(openLink, settingsLink);

            card.append(body, actions);

            fragment.appendChild(card);
        });

        state.courseList.appendChild(fragment);
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
        return {    
            token,
            user,
        };
    };

    const loadCourses = async (token) => {
        if (!state.courseList) return;

        const response = await fetch('/api/courses', {
            method: 'GET',
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });

        if (response.status === 401) {
            clearToken();
            redirectHome();
            return;
        }

        if (!response.ok) {
            throw new Error('Не удалось загрузить курсы.');
        }

        const courses = await response.json();
        renderCourses(courses);
    };

    const getMessageBox = (form) => form.querySelector('#course-form-message');

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

    const validateCourseForm = (form) => {
        const title = form.querySelector('#course-title');
        const description = form.querySelector('#course-description');
        const slug = form.querySelector('#course-slug');

        clearFieldError(form, 'title');
        clearFieldError(form, 'description');
        clearFieldError(form, 'slug');

        const values = {
            title: title ? title.value.trim() : '',
            description: description ? description.value.trim() : '',
            slug: slug ? slug.value.trim() : '',
        };

        let firstInvalid = null;

        if (!values.title) {
            setFieldError(form, 'title', 'Название курса обязательно.');
            firstInvalid = firstInvalid || title;
        } else if (values.title.length < 3) {
            setFieldError(form, 'title', 'Название курса должно содержать минимум 3 символа.');
            firstInvalid = firstInvalid || title;
        }

        if (!values.description) {
            setFieldError(form, 'description', 'Краткое описание обязательно.');
            firstInvalid = firstInvalid || description;
        } else if (values.description.length < 10) {
            setFieldError(form, 'description', 'Описание должно содержать минимум 10 символов.');
            firstInvalid = firstInvalid || description;
        }

        if (!values.slug) {
            setFieldError(form, 'slug', 'Слаг обязателен.');
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

    const initCourseForm = () => {
        const form = document.querySelector('[data-course-form]');

        if (!form) {
            return;
        }

        const title = form.querySelector('#course-title');
        const slug = form.querySelector('#course-slug');
        const messageBox = getMessageBox(form);
        let slugTouched = Boolean(slug && slug.value.trim());

        if (title && slug) {
            title.addEventListener('input', () => {
                if (!slugTouched) {
                    slug.value = slugify(title.value);
                }
                clearFieldError(form, 'title');
                clearFormMessage(messageBox);
            });

            slug.addEventListener('input', () => {
                slugTouched = Boolean(slug.value.trim());
                clearFieldError(form, 'slug');
                clearFormMessage(messageBox);
            });
        }

        ['title', 'description', 'slug'].forEach((fieldName) => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (!field) return;

            field.addEventListener('input', () => {
                clearFieldError(form, fieldName);
            });
        });

        form.addEventListener('submit', (event) => {
            event.preventDefault();

            clearFormMessage(messageBox);

            const result = validateCourseForm(form);

            if (!result.valid) {
                setFormMessage(messageBox, 'is-error', 'Проверьте выделенные поля.');
                if (result.firstInvalid) {
                    result.firstInvalid.focus();
                }
                return;
            }

            setFormMessage(messageBox, 'is-success', 'Проверка пройдена. Дальнейшая отправка подключится позже.');
        });
    };

    const initAdminShell = async () => {
        state.content = document.querySelector('[data-admin-content]');
        state.loading = document.querySelector('[data-admin-loading]');
        state.error = document.querySelector('[data-admin-error]');
        state.courseList = document.querySelector('[data-course-list]');

        hideError();
        hideContent();
        showLoading();

        try {
            const access = await checkAdminAccess();

            if (!access) {
                return;
            }

            if (state.courseList) {
                await loadCourses(access.token);
            }

            hideLoading();
            showContent();
        } catch (error) {
            hideLoading();
            showError('Не удалось проверить доступ. Выполните вход заново.');
            redirectHome();
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        initAdminShell();
        initCourseForm();
    });
})();
