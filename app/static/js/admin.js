(function () {
    const TOKEN_KEY = 'musa_code_academy_token';

    const state = {
        content: null,
        loading: null,
        error: null,
        notification: null,
        courseList: null,
        activeMenu: null,
        deleteDialog: null,
        pendingDeleteCourseId: null,
        notificationTimer: null,
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

    const getCourseUrl = (courseId) => `/admin/courses/${courseId}`;

    const getCourseEditUrl = (courseId) => `/admin/courses/${courseId}/edit`;

    const hideNotification = () => {
        if (state.notificationTimer) {
            window.clearTimeout(state.notificationTimer);
            state.notificationTimer = null;
        }

        if (!state.notification) {
            return;
        }

        state.notification.hidden = true;
        state.notification.innerHTML = '';
    };

    const showNotification = (message, kind) => {
        if (!state.notification) {
            return;
        }

        hideNotification();

        const toast = document.createElement('div');
        toast.className = `admin-notification admin-notification--${kind} is-visible`;
        toast.setAttribute('role', kind === 'error' ? 'alert' : 'status');
        toast.textContent = message;

        state.notification.hidden = false;
        state.notification.appendChild(toast);
        state.notificationTimer = window.setTimeout(hideNotification, 4000);
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

    const removeCourseCard = (courseId) => {
        if (!state.courseList) {
            return;
        }

        const card = state.courseList.querySelector(`[data-course-id="${courseId}"]`);
        if (card) {
            card.remove();
        }

        if (!state.courseList.querySelector('.course-card')) {
            state.courseList.innerHTML = `
                <div class="empty-state" role="status">
                    <p class="empty-state__title">Курсы отсутствуют</p>
                </div>
            `;
        }
    };

    const closeActiveMenu = () => {
        if (!state.activeMenu) {
            return;
        }

        const { card, trigger, menu } = state.activeMenu;

        if (trigger) {
            trigger.setAttribute('aria-expanded', 'false');
        }

        if (menu) {
            menu.hidden = true;
        }

        if (card) {
            card.classList.remove('is-menu-open');
        }

        state.activeMenu = null;
    };

    const openMenuForCard = (card) => {
        const trigger = card.querySelector('[data-course-menu-trigger]');
        const menu = card.querySelector('[data-course-menu]');

        if (!trigger || !menu) {
            return;
        }

        if (state.activeMenu && state.activeMenu.card !== card) {
            closeActiveMenu();
        }

        const isOpen = state.activeMenu && state.activeMenu.card === card;

        if (isOpen) {
            closeActiveMenu();
            return;
        }

        trigger.setAttribute('aria-expanded', 'true');
        menu.hidden = false;
        card.classList.add('is-menu-open');
        state.activeMenu = { card, trigger, menu };
    };

    const deleteCourse = async (courseId) => {
        const token = getToken();

        if (!token) {
            throw new Error('Failed to delete the course.');
        }

        const response = await fetch(`/api/courses/${courseId}`, {
            method: 'DELETE',
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });

        if (!response.ok) {
            const fallbackMessage = 'Failed to delete the course.';
            const errorMessage = await getBackendErrorMessage(response, fallbackMessage);
            throw new Error(errorMessage || fallbackMessage);
        }

        removeCourseCard(courseId);
    };

    const showDeleteDialog = (courseId) => {
        if (!state.deleteDialog) {
            const dialog = document.createElement('div');
            dialog.className = 'dialog-overlay';
            dialog.hidden = true;
            dialog.innerHTML = `
                <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="delete-course-title" aria-describedby="delete-course-description">
                    <h2 id="delete-course-title">Delete this course?</h2>
                    <p id="delete-course-description">This action cannot be undone.</p>
                    <div class="dialog__actions">
                        <button type="button" class="button button--ghost" data-delete-cancel>Cancel</button>
                        <button type="button" class="button button--danger" data-delete-confirm>Delete</button>
                    </div>
                </div>
            `;
            document.body.appendChild(dialog);
            state.deleteDialog = dialog;

            dialog.addEventListener('click', (event) => {
                if (event.target === dialog) {
                    dialog.hidden = true;
                    state.pendingDeleteCourseId = null;
                }
            });

            dialog.querySelector('[data-delete-cancel]')?.addEventListener('click', () => {
                dialog.hidden = true;
                state.pendingDeleteCourseId = null;
            });

            dialog.querySelector('[data-delete-confirm]')?.addEventListener('click', async () => {
                const confirmButton = dialog.querySelector('[data-delete-confirm]');
                const cancelButton = dialog.querySelector('[data-delete-cancel]');
                const targetCourseId = state.pendingDeleteCourseId;

                if (!targetCourseId) {
                    dialog.hidden = true;
                    return;
                }

                if (confirmButton instanceof HTMLButtonElement) {
                    confirmButton.disabled = true;
                }

                if (cancelButton instanceof HTMLButtonElement) {
                    cancelButton.disabled = true;
                }

                try {
                    await deleteCourse(targetCourseId);
                    dialog.hidden = true;
                    state.pendingDeleteCourseId = null;
                    showNotification('Course deleted successfully.', 'success');
                } catch (error) {
                    dialog.hidden = true;
                    state.pendingDeleteCourseId = null;
                    showNotification(
                        error instanceof Error && error.message ? error.message : 'Failed to delete the course.',
                        'error'
                    );
                } finally {
                    if (confirmButton instanceof HTMLButtonElement) {
                        confirmButton.disabled = false;
                    }

                    if (cancelButton instanceof HTMLButtonElement) {
                        cancelButton.disabled = false;
                    }
                }
            });

            document.addEventListener('keydown', (event) => {
                if (event.key === 'Escape' && state.deleteDialog && !state.deleteDialog.hidden) {
                    state.deleteDialog.hidden = true;
                    state.pendingDeleteCourseId = null;
                }
            });
        }

        state.pendingDeleteCourseId = courseId;
        state.deleteDialog.hidden = false;
        state.deleteDialog.querySelector('[data-delete-cancel]')?.focus();
    };

    const handleCourseListClick = (event) => {
        const menuButton = event.target.closest('[data-course-menu-trigger]');
        if (menuButton) {
            event.preventDefault();
            event.stopPropagation();
            const card = menuButton.closest('.course-card');
            if (card) {
                openMenuForCard(card);
            }
            return;
        }

        const menuItem = event.target.closest('[data-course-menu-item]');
        if (menuItem) {
            event.preventDefault();
            event.stopPropagation();

            const card = menuItem.closest('.course-card');
            const courseId = card?.dataset.courseId;
            const action = menuItem.dataset.courseMenuItem;

            closeActiveMenu();

            if (!courseId) {
                return;
            }

            if (action === 'edit') {
                window.location.href = getCourseEditUrl(courseId);
            } else if (action === 'delete') {
                showDeleteDialog(courseId);
            }

            return;
        }

        const menu = event.target.closest('[data-course-menu]');
        if (menu) {
            event.stopPropagation();
            return;
        }

        const card = event.target.closest('.course-card');
        if (card && state.courseList?.contains(card)) {
            const courseId = card.dataset.courseId;

            if (courseId) {
                closeActiveMenu();
                window.location.href = getCourseUrl(courseId);
            }
        }
    };

    const handleDocumentClick = (event) => {
        if (!state.activeMenu) {
            return;
        }

        const clickedInsideCard = event.target.closest('.course-card') === state.activeMenu.card;

        if (!clickedInsideCard) {
            closeActiveMenu();
            return;
        }

        const clickedTrigger = event.target.closest('[data-course-menu-trigger]');
        const clickedMenu = event.target.closest('[data-course-menu]');

        if (!clickedTrigger && !clickedMenu) {
            closeActiveMenu();
        }
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

        closeActiveMenu();
        state.courseList.innerHTML = '';

        if (!Array.isArray(courses) || courses.length === 0) {
            state.courseList.innerHTML = `
                <div class="empty-state" role="status">
                    <p class="empty-state__title">Курсы отсутствуют</p>
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
            card.dataset.courseId = String(course.id ?? '');
            card.tabIndex = 0;

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

            const description = document.createElement('p');
            description.className = 'course-card__description';
            description.textContent = course.short_description ?? '';
            body.append(description);

            const actions = document.createElement('div');
            actions.className = 'course-card__actions';

            const menuWrap = document.createElement('div');
            menuWrap.className = 'course-card__menu-wrap';

            const menuButton = document.createElement('button');
            menuButton.className = 'course-card__menu-button';
            menuButton.type = 'button';
            menuButton.setAttribute('aria-label', 'Открыть меню курса');
            menuButton.setAttribute('aria-haspopup', 'menu');
            menuButton.setAttribute('aria-expanded', 'false');
            menuButton.setAttribute('data-course-menu-trigger', '');
            menuButton.textContent = '⋮';

            const menu = document.createElement('div');
            menu.className = 'course-card__menu';
            menu.hidden = true;
            menu.setAttribute('data-course-menu', '');
            menu.setAttribute('role', 'menu');
            menu.innerHTML = `
                <button type="button" class="course-card__menu-item" data-course-menu-item="edit" role="menuitem">Edit</button>
                <button type="button" class="course-card__menu-item course-card__menu-item--danger" data-course-menu-item="delete" role="menuitem">Delete</button>
            `;

            menuWrap.append(menuButton, menu);
            actions.append(menuWrap);

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

    const showCoursesLoading = () => {
        hideError();
        hideContent();
        showLoading('Загрузка курсов...');
    };

    const showCoursesError = () => {
        hideLoading();
        showError('Не удалось загрузить список курсов');
    };

    const loadCourses = async () => {
        if (!state.courseList) return;

        const token = getToken();

        if (!token) {
            redirectHome();
            return;
        }

        showCoursesLoading();

        try {
            const response = await fetch('/api/courses/admin', {
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
                throw new Error('Не удалось загрузить список курсов');
            }

            const courses = await response.json();
            renderCourses(Array.isArray(courses) ? courses : []);
            hideLoading();
            showContent();
        } catch (error) {
            showCoursesError();
        }
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
            submitButton.textContent = isBusy ? 'Создание...' : 'Создать курс';
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

    const initCourseForm = () => {
        const form = document.querySelector('[data-course-form]');

        if (!form) {
            return;
        }

        const title = form.querySelector('#course-title');
        const shortDescription = form.querySelector('#course-short-description');
        const description = form.querySelector('#course-description');
        const slug = form.querySelector('#course-slug');
        const messageBox = getMessageBox(form);
        const progressBar = getProgressBar(form);
        let slugTouched = Boolean(slug && slug.value.trim());
        let isSubmitting = false;

        if (progressBar) {
            progressBar.hidden = true;
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

        ['title', 'short_description', 'description', 'slug'].forEach((fieldName) => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (!field) return;

            field.addEventListener('input', () => {
                clearFieldError(form, fieldName);
            });
        });

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
            };

            isSubmitting = true;
            setFormBusy(form, true);

            try {
                const response = await fetch('/api/courses', {
                    method: 'POST',
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
                        'Failed to create the course.'
                    );

                    throw new Error(errorMessage || 'Failed to create the course.');
                }

                window.location.href = '/admin';
            } catch (error) {
                showNotification(
                    error instanceof Error && error.message
                        ? error.message
                        : 'Failed to create the course.',
                    'error'
                );
            } finally {
                isSubmitting = false;
                setFormBusy(form, false);
            }
        });
    };

    const initAdminShell = async () => {
        state.content = document.querySelector('[data-admin-content]');
        state.loading = document.querySelector('[data-admin-loading]');
        state.error = document.querySelector('[data-admin-error]');
        state.notification = document.querySelector('[data-admin-notifications]');
        state.courseList = document.querySelector('[data-course-list]');

        hideError();
        hideNotification();
        hideContent();
        showLoading();

        if (state.courseList) {
            state.courseList.addEventListener('click', handleCourseListClick);
            state.courseList.addEventListener('keydown', (event) => {
                if (event.key !== 'Enter' && event.key !== ' ') {
                    return;
                }

                const card = event.target.closest('.course-card');
                if (!card || event.target.closest('[data-course-menu-trigger]') || event.target.closest('[data-course-menu]')) {
                    return;
                }

                const courseId = card.dataset.courseId;
                if (!courseId) {
                    return;
                }

                event.preventDefault();
                closeActiveMenu();
                window.location.href = getCourseUrl(courseId);
            });
        }

        document.addEventListener('click', handleDocumentClick);

        try {
            const access = await checkAdminAccess();

            if (!access) {
                return;
            }

            if (state.courseList) {
                await loadCourses();
                return;
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
