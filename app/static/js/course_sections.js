(function () {
    const TOKEN_KEY = 'musa_code_academy_token';

    const state = {
        courseId: null,
        sections: [],
        activeMenu: null,
        editingSectionId: null,
        pendingDeleteSectionId: null,
        deleteDialog: null,
        notificationTimer: null,
        loading: null,
        error: null,
        content: null,
        courseTitle: null,
        sectionList: null,
        notification: null,
        newSectionButton: null,
        createForm: null,
    };

    const getToken = () => localStorage.getItem(TOKEN_KEY);

    const clearToken = () => localStorage.removeItem(TOKEN_KEY);

    const redirectHome = () => {
        window.location.href = '/';
    };

    const getCourseId = () => {
        const value = state.content?.dataset.courseId;
        return value && /^\d+$/.test(value) ? value : null;
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

    const showLoading = (message) => {
        state.loading.hidden = false;
        state.loading.textContent = message;
    };

    const showError = (message) => {
        state.loading.hidden = true;
        state.content.hidden = true;
        state.error.hidden = false;
        state.error.textContent = message;
    };

    const showContent = () => {
        state.loading.hidden = true;
        state.error.hidden = true;
        state.error.textContent = '';
        state.content.hidden = false;
    };

    const hideNotification = () => {
        if (state.notificationTimer) {
            window.clearTimeout(state.notificationTimer);
            state.notificationTimer = null;
        }

        state.notification.innerHTML = '';
    };

    const showNotification = (message, kind) => {
        hideNotification();

        const toast = document.createElement('div');
        toast.className = `admin-notification admin-notification--${kind} is-visible`;
        toast.setAttribute('role', kind === 'error' ? 'alert' : 'status');
        toast.textContent = message;

        state.notification.appendChild(toast);
        state.notificationTimer = window.setTimeout(hideNotification, 4000);
    };

    const closeActiveMenu = () => {
        if (!state.activeMenu) {
            return;
        }

        state.activeMenu.trigger.setAttribute('aria-expanded', 'false');
        state.activeMenu.menu.hidden = true;
        state.activeMenu.item.classList.remove('is-menu-open');
        state.activeMenu = null;
    };

    const toggleMenu = (item) => {
        const trigger = item.querySelector('[data-section-menu-trigger]');
        const menu = item.querySelector('[data-section-menu]');

        if (!trigger || !menu) {
            return;
        }

        if (state.activeMenu?.item === item) {
            closeActiveMenu();
            return;
        }

        closeActiveMenu();
        trigger.setAttribute('aria-expanded', 'true');
        menu.hidden = false;
        item.classList.add('is-menu-open');
        state.activeMenu = { item, trigger, menu };
    };

    const closeCreateForm = () => {
        state.createForm.hidden = true;
        state.createForm.reset();
        state.createForm.querySelector('[name="title"]')?.removeAttribute('aria-invalid');
        state.createForm.querySelector('[name="description"]')?.removeAttribute('aria-invalid');
        state.createForm.querySelector('[data-title-error]').textContent = '';
        state.createForm.querySelector('[data-description-error]').textContent = '';
        state.newSectionButton.hidden = false;
    };

    const closeEditor = () => {
        if (state.editingSectionId === null) {
            return;
        }

        state.editingSectionId = null;
        renderSections();
    };

    const openCreateForm = () => {
        closeActiveMenu();
        closeEditor();
        state.newSectionButton.hidden = true;
        state.createForm.hidden = false;
        state.createForm.querySelector('[name="title"]')?.focus();
    };

    const validateSectionForm = (form) => {
        const titleInput = form.querySelector('[name="title"]');
        const descriptionInput = form.querySelector('[name="description"]');
        const titleError = form.querySelector('[data-title-error]');
        const descriptionError = form.querySelector('[data-description-error]');
        const title = titleInput?.value.trim() ?? '';
        const description = descriptionInput?.value.trim() ?? '';
        let titleMessage = '';
        let descriptionMessage = '';

        if (!title) {
            titleMessage = 'Section title is required.';
        } else if (title.length < 3) {
            titleMessage = 'Section title must contain at least 3 characters.';
        } else if (title.length > 255) {
            titleMessage = 'Section title must contain no more than 255 characters.';
        }

        if (description && description.length < 10) {
            descriptionMessage = 'Description must contain at least 10 characters.';
        }

        titleInput?.toggleAttribute('aria-invalid', Boolean(titleMessage));
        descriptionInput?.toggleAttribute('aria-invalid', Boolean(descriptionMessage));
        titleError.textContent = titleMessage;
        descriptionError.textContent = descriptionMessage;

        if (titleMessage) {
            titleInput?.focus();
            return null;
        }

        if (descriptionMessage) {
            descriptionInput?.focus();
            return null;
        }

        return { title, description };
    };

    const createInlineEditor = (section) => {
        const form = document.createElement('form');
        form.className = 'inline-section-form inline-section-form--edit';
        form.dataset.editForm = String(section.id);
        form.noValidate = true;
        form.innerHTML = `
            <div class="field">
                <label for="section-title-${section.id}">Section title</label>
                <input
                    id="section-title-${section.id}"
                    name="title"
                    type="text"
                    minlength="3"
                    maxlength="255"
                    autocomplete="off"
                    required
                >
                <p class="field-error" data-title-error aria-live="polite"></p>
            </div>
            <div class="field">
                <label for="section-description-${section.id}">Description</label>
                <textarea
                    id="section-description-${section.id}"
                    name="description"
                    rows="4"
                    minlength="10"
                    placeholder="Briefly describe what this section covers"
                ></textarea>
                <p class="field-error" data-description-error aria-live="polite"></p>
            </div>
            <div class="form-actions">
                <button class="button button--primary" type="submit">Save</button>
                <button class="button button--ghost" type="button" data-edit-cancel>Cancel</button>
            </div>
        `;
        form.querySelector('[name="title"]').value = section.title ?? '';
        form.querySelector('[name="description"]').value = section.description ?? '';
        return form;
    };

    const createSectionItem = (section) => {
        const item = document.createElement('article');
        item.className = 'section-item';
        item.dataset.sectionId = String(section.id);
        item.setAttribute('role', 'listitem');

        const row = document.createElement('div');
        row.className = 'section-row';

        const dragHandle = document.createElement('span');
        dragHandle.className = 'section-row__drag-handle';
        dragHandle.setAttribute('aria-hidden', 'true');
        dragHandle.title = 'Drag to reorder';
        dragHandle.innerHTML = '<span></span><span></span><span></span><span></span><span></span><span></span>';

        const body = document.createElement('div');
        body.className = 'section-row__body';

        const title = document.createElement('button');
        title.className = 'section-row__title';
        title.type = 'button';
        title.dataset.sectionTitle = '';
        title.textContent = section.title ?? 'Untitled section';
        title.setAttribute('aria-label', `${title.textContent}. Section page coming later.`);

        const description = document.createElement('p');
        description.className = 'section-row__description';
        description.textContent = section.description ?? 'No description';

        body.append(title, description);

        const menuWrap = document.createElement('div');
        menuWrap.className = 'section-row__menu-wrap';

        const menuButton = document.createElement('button');
        menuButton.className = 'section-row__menu-button';
        menuButton.type = 'button';
        menuButton.dataset.sectionMenuTrigger = '';
        menuButton.setAttribute('aria-label', `Open menu for ${title.textContent}`);
        menuButton.setAttribute('aria-haspopup', 'menu');
        menuButton.setAttribute('aria-expanded', 'false');
        menuButton.textContent = '⋮';

        const menu = document.createElement('div');
        menu.className = 'section-row__menu';
        menu.dataset.sectionMenu = '';
        menu.setAttribute('role', 'menu');
        menu.hidden = true;
        menu.innerHTML = `
            <button type="button" class="section-row__menu-item" data-section-action="edit" role="menuitem">Edit</button>
            <button type="button" class="section-row__menu-item section-row__menu-item--danger" data-section-action="delete" role="menuitem">Delete</button>
        `;

        menuWrap.append(menuButton, menu);
        row.append(dragHandle, body, menuWrap);
        item.appendChild(row);

        if (state.editingSectionId === String(section.id)) {
            item.classList.add('is-editing');
            item.appendChild(createInlineEditor(section));
        }

        return item;
    };

    const renderSections = () => {
        closeActiveMenu();
        state.sectionList.innerHTML = '';

        if (state.sections.length === 0) {
            state.sectionList.innerHTML = `
                <div class="empty-state" role="status">
                    <p class="empty-state__title">No sections yet</p>
                </div>
            `;
            return;
        }

        const fragment = document.createDocumentFragment();
        state.sections.forEach((section) => fragment.appendChild(createSectionItem(section)));
        state.sectionList.appendChild(fragment);

        if (state.editingSectionId !== null) {
            state.sectionList
                .querySelector(`[data-edit-form="${state.editingSectionId}"] [name="title"]`)
                ?.focus();
        }
    };

    const openEditor = (sectionId) => {
        closeActiveMenu();
        closeCreateForm();
        state.editingSectionId = sectionId;
        renderSections();
    };

    const deleteSection = async (sectionId) => {
        const response = await fetch(`/api/sections/${sectionId}/admin`, {
            method: 'DELETE',
            headers: {
                Authorization: `Bearer ${getToken()}`,
            },
        });

        if (response.status === 401) {
            clearToken();
            redirectHome();
            return false;
        }

        if (!response.ok) {
            const message = await getBackendErrorMessage(response, 'Failed to delete section.');
            throw new Error(message);
        }

        state.sections = state.sections.filter((section) => String(section.id) !== sectionId);
        if (state.editingSectionId === sectionId) {
            state.editingSectionId = null;
        }
        renderSections();
        return true;
    };

    const closeDeleteDialog = () => {
        state.deleteDialog.hidden = true;
        state.pendingDeleteSectionId = null;
    };

    const showDeleteDialog = (sectionId) => {
        state.pendingDeleteSectionId = sectionId;
        state.deleteDialog.hidden = false;
        state.deleteDialog.querySelector('[data-delete-cancel]')?.focus();
    };

    const buildDeleteDialog = () => {
        const overlay = document.createElement('div');
        overlay.className = 'dialog-overlay';
        overlay.hidden = true;
        overlay.innerHTML = `
            <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="delete-section-title" aria-describedby="delete-section-description">
                <h2 id="delete-section-title">Delete this section?</h2>
                <p id="delete-section-description">This action cannot be undone.</p>
                <div class="dialog__actions">
                    <button type="button" class="button button--ghost" data-delete-cancel>Cancel</button>
                    <button type="button" class="button button--danger" data-delete-confirm>Delete</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        state.deleteDialog = overlay;

        overlay.addEventListener('click', (event) => {
            if (event.target === overlay) {
                closeDeleteDialog();
            }
        });

        overlay.querySelector('[data-delete-cancel]').addEventListener('click', closeDeleteDialog);
        overlay.querySelector('[data-delete-confirm]').addEventListener('click', async (event) => {
            const confirmButton = event.currentTarget;
            const cancelButton = overlay.querySelector('[data-delete-cancel]');
            const sectionId = state.pendingDeleteSectionId;

            if (!sectionId) {
                closeDeleteDialog();
                return;
            }

            confirmButton.disabled = true;
            cancelButton.disabled = true;

            try {
                const deleted = await deleteSection(sectionId);
                closeDeleteDialog();
                if (deleted) {
                    showNotification('Section deleted.', 'success');
                }
            } catch (error) {
                closeDeleteDialog();
                showNotification(error.message || 'Failed to delete section.', 'error');
            } finally {
                confirmButton.disabled = false;
                cancelButton.disabled = false;
            }
        });
    };

    const handleSectionListClick = (event) => {
        const menuTrigger = event.target.closest('[data-section-menu-trigger]');
        if (menuTrigger) {
            toggleMenu(menuTrigger.closest('.section-item'));
            return;
        }

        const actionButton = event.target.closest('[data-section-action]');
        if (actionButton) {
            const sectionId = actionButton.closest('.section-item')?.dataset.sectionId;
            const action = actionButton.dataset.sectionAction;

            closeActiveMenu();
            if (!sectionId) {
                return;
            }

            if (action === 'edit') {
                openEditor(sectionId);
            } else if (action === 'delete') {
                showDeleteDialog(sectionId);
            }
            return;
        }

        if (event.target.closest('[data-edit-cancel]')) {
            closeEditor();
        }
    };

    const handleEditSubmit = async (event) => {
        const form = event.target.closest('[data-edit-form]');
        if (!form) {
            return;
        }

        event.preventDefault();
        const values = validateSectionForm(form);
        if (!values) {
            return;
        }

        const sectionId = form.dataset.editForm;
        const submitButton = form.querySelector('[type="submit"]');
        const cancelButton = form.querySelector('[data-edit-cancel]');
        submitButton.disabled = true;
        cancelButton.disabled = true;
        submitButton.textContent = 'Saving...';

        try {
            const response = await fetch(`/api/sections/${sectionId}/admin`, {
                method: 'PATCH',
                headers: {
                    Authorization: `Bearer ${getToken()}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: values.title,
                    description: values.description || null,
                }),
            });

            if (response.status === 401) {
                clearToken();
                redirectHome();
                return;
            }

            if (!response.ok) {
                const message = await getBackendErrorMessage(response, 'Failed to update section.');
                throw new Error(message);
            }

            const updatedSection = await response.json();
            state.sections = state.sections.map((section) =>
                String(section.id) === sectionId ? updatedSection : section
            );
            state.editingSectionId = null;
            renderSections();
            showNotification('Section updated.', 'success');
        } catch (error) {
            showNotification(error.message || 'Failed to update section.', 'error');
        } finally {
            submitButton.disabled = false;
            cancelButton.disabled = false;
            submitButton.textContent = 'Save';
        }
    };

    const handleCreateSubmit = async (event) => {
        event.preventDefault();
        const values = validateSectionForm(state.createForm);
        if (!values) {
            return;
        }

        const submitButton = state.createForm.querySelector('[data-create-submit]');
        const cancelButton = state.createForm.querySelector('[data-create-cancel]');
        submitButton.disabled = true;
        cancelButton.disabled = true;
        submitButton.textContent = 'Creating...';

        try {
            const response = await fetch(`/api/courses/${state.courseId}/sections`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${getToken()}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: values.title,
                    description: values.description || null,
                }),
            });

            if (response.status === 401) {
                clearToken();
                redirectHome();
                return;
            }

            if (!response.ok) {
                const message = await getBackendErrorMessage(response, 'Failed to create section.');
                throw new Error(message);
            }

            const section = await response.json();
            state.sections.push(section);
            closeCreateForm();
            renderSections();
            showNotification('Section created.', 'success');
        } catch (error) {
            showNotification(error.message || 'Failed to create section.', 'error');
        } finally {
            submitButton.disabled = false;
            cancelButton.disabled = false;
            submitButton.textContent = 'Create';
        }
    };

    const checkAdminAccess = async () => {
        const token = getToken();
        if (!token) {
            redirectHome();
            return false;
        }

        const response = await fetch('/api/users/me', {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });

        if (response.status === 401) {
            clearToken();
            redirectHome();
            return false;
        }

        if (!response.ok) {
            redirectHome();
            return false;
        }

        const user = await response.json();
        if (user.role !== 'admin') {
            redirectHome();
            return false;
        }

        return true;
    };

    const loadCourseStructure = async () => {
        showLoading('Loading course...');
        const token = getToken();
        const headers = {
            Authorization: `Bearer ${token}`,
        };

        const [courseResponse, sectionsResponse] = await Promise.all([
            fetch(`/api/courses/${state.courseId}/admin`, { headers }),
            fetch(`/api/courses/${state.courseId}/sections/admin`, { headers }),
        ]);

        if (courseResponse.status === 401 || sectionsResponse.status === 401) {
            clearToken();
            redirectHome();
            return;
        }

        if (!courseResponse.ok) {
            const message = await getBackendErrorMessage(courseResponse, 'Failed to load course.');
            throw new Error(message);
        }

        if (!sectionsResponse.ok) {
            const message = await getBackendErrorMessage(sectionsResponse, 'Failed to load sections.');
            throw new Error(message);
        }

        const [course, sections] = await Promise.all([
            courseResponse.json(),
            sectionsResponse.json(),
        ]);

        state.courseTitle.textContent = course.title ?? 'Untitled course';
        document.title = `${state.courseTitle.textContent} — Sections`;
        state.sections = Array.isArray(sections) ? sections : [];
        renderSections();
        showContent();
    };

    const handleDocumentClick = (event) => {
        if (
            state.activeMenu &&
            !event.target.closest('[data-section-menu]') &&
            !event.target.closest('[data-section-menu-trigger]')
        ) {
            closeActiveMenu();
        }
    };

    const handleKeydown = (event) => {
        if (event.key !== 'Escape') {
            return;
        }

        if (!state.deleteDialog.hidden) {
            closeDeleteDialog();
        } else if (state.activeMenu) {
            closeActiveMenu();
        } else if (state.editingSectionId !== null) {
            closeEditor();
        } else if (!state.createForm.hidden) {
            closeCreateForm();
        }
    };

    const init = async () => {
        state.loading = document.querySelector('[data-admin-loading]');
        state.error = document.querySelector('[data-admin-error]');
        state.content = document.querySelector('[data-admin-content]');
        state.courseTitle = document.querySelector('[data-course-title]');
        state.sectionList = document.querySelector('[data-section-list]');
        state.notification = document.querySelector('[data-admin-notifications]');
        state.newSectionButton = document.querySelector('[data-new-section]');
        state.createForm = document.querySelector('[data-create-form]');
        state.courseId = getCourseId();

        buildDeleteDialog();
        state.sectionList.addEventListener('click', handleSectionListClick);
        state.sectionList.addEventListener('submit', handleEditSubmit);
        state.newSectionButton.addEventListener('click', openCreateForm);
        state.createForm.addEventListener('submit', handleCreateSubmit);
        state.createForm
            .querySelector('[data-create-cancel]')
            .addEventListener('click', closeCreateForm);
        document.addEventListener('click', handleDocumentClick);
        document.addEventListener('keydown', handleKeydown);

        if (!state.courseId) {
            showError('Invalid course ID.');
            return;
        }

        try {
            const hasAccess = await checkAdminAccess();
            if (hasAccess) {
                await loadCourseStructure();
            }
        } catch (error) {
            showError(error.message || 'Failed to load course structure.');
        }
    };

    document.addEventListener('DOMContentLoaded', init);
})();
