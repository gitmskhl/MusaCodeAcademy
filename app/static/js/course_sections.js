(function () {
    const TOKEN_KEY = 'musa_code_academy_token';

    const state = {
        courseId: null,
        sectionId: null,
        config: null,
        items: [],
        activeMenu: null,
        editingItemId: null,
        pendingDeleteItemId: null,
        deleteDialog: null,
        notificationTimer: null,
        loading: null,
        error: null,
        content: null,
        structureTitle: null,
        listTitle: null,
        itemList: null,
        sortable: null,
        notification: null,
        backLink: null,
        newItemButton: null,
        createForm: null,
    };

    const getToken = () => localStorage.getItem(TOKEN_KEY);

    const clearToken = () => localStorage.removeItem(TOKEN_KEY);

    const redirectHome = () => {
        window.location.href = '/';
    };

    const getNumericValue = (value) => (value && /^\d+$/.test(value) ? value : null);

    const getCourseId = () => getNumericValue(state.content?.dataset.courseId);

    const getSectionId = () => {
        const searchParams = new URLSearchParams(window.location.search);
        return getNumericValue(searchParams.get('section'));
    };

    const getCourseUrl = () => `/admin/courses/${encodeURIComponent(state.courseId)}`;

    const getLessonsUrl = (sectionId) =>
        `${getCourseUrl()}?section=${encodeURIComponent(sectionId)}`;

    const getLessonStepsUrl = (lessonId) =>
        `/admin/lessons/${encodeURIComponent(lessonId)}`;

    const createConfig = () => {
        if (state.sectionId) {
            return {
                kind: 'lesson',
                singular: 'Lesson',
                singularLower: 'lesson',
                plural: 'Lessons',
                pluralLower: 'lessons',
                backText: '← Назад к разделам',
                backUrl: getCourseUrl(),
                listTitle: 'Уроки',
                newButtonText: 'Добавить урок',
                titleLabel: 'Название урока',
                descriptionLabel: 'Описание',
                descriptionPlaceholder: 'Кратко опишите содержание урока',
                emptyText: 'Уроков пока нет',
                parentLoadingText: 'Загрузка раздела...',
                parentFallback: 'Раздел без названия',
                pageSuffix: 'Уроки',
                parentUrl: `/api/sections/${state.sectionId}/admin`,
                itemsUrl: `/api/sections/${state.sectionId}/admin/lessons`,
                createUrl: `/api/sections/${state.sectionId}/admin/lessons`,
                orderUrl: '/api/lessons/admin/order',
                orderPayloadKey: 'lessons',
                itemUrl: (itemId) => `/api/lessons/${itemId}/admin`,
                itemDestination: getLessonStepsUrl,
            };
        }

        return {
            kind: 'section',
            singular: 'Section',
            singularLower: 'section',
            plural: 'Sections',
            pluralLower: 'sections',
            backText: '← Back to courses',
            backUrl: '/admin',
            listTitle: 'Sections',
            newButtonText: '+ New Section',
            titleLabel: 'Section title',
            descriptionLabel: 'Description',
            descriptionPlaceholder: 'Briefly describe what this section covers',
            emptyText: 'No sections yet',
            parentLoadingText: 'Loading course...',
            parentFallback: 'Untitled course',
            pageSuffix: 'Sections',
            parentUrl: `/api/courses/${state.courseId}/admin`,
            itemsUrl: `/api/courses/${state.courseId}/sections/admin`,
            createUrl: `/api/courses/${state.courseId}/sections`,
            orderUrl: '/api/sections/admin/order',
            orderPayloadKey: 'sections',
            itemUrl: (itemId) => `/api/sections/${itemId}/admin`,
            itemDestination: getLessonsUrl,
        };
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
        const trigger = item.querySelector('[data-item-menu-trigger]');
        const menu = item.querySelector('[data-item-menu]');

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

    const clearFormErrors = (form) => {
        form.querySelector('[name="title"]')?.removeAttribute('aria-invalid');
        form.querySelector('[name="description"]')?.removeAttribute('aria-invalid');
        form.querySelector('[data-title-error]').textContent = '';
        form.querySelector('[data-description-error]').textContent = '';
    };

    const closeCreateForm = () => {
        state.createForm.hidden = true;
        state.createForm.reset();
        clearFormErrors(state.createForm);
        state.newItemButton.hidden = false;
    };

    const closeEditor = () => {
        if (state.editingItemId === null) {
            return;
        }

        state.editingItemId = null;
        renderItems();
    };

    const openCreateForm = () => {
        closeActiveMenu();
        closeEditor();
        state.newItemButton.hidden = true;
        state.createForm.hidden = false;
        state.createForm.querySelector('[name="title"]')?.focus();
    };

    const validateItemForm = (form) => {
        const titleInput = form.querySelector('[name="title"]');
        const descriptionInput = form.querySelector('[name="description"]');
        const titleError = form.querySelector('[data-title-error]');
        const descriptionError = form.querySelector('[data-description-error]');
        const title = titleInput?.value.trim() ?? '';
        const description = descriptionInput?.value.trim() ?? '';
        let titleMessage = '';
        let descriptionMessage = '';

        if (!title) {
            titleMessage = `${state.config.singular} title is required.`;
        } else if (title.length < 3) {
            titleMessage = `${state.config.singular} title must contain at least 3 characters.`;
        } else if (title.length > 255) {
            titleMessage = `${state.config.singular} title must contain no more than 255 characters.`;
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

    const createInlineEditor = (item) => {
        const form = document.createElement('form');
        form.className = 'inline-section-form inline-section-form--edit';
        form.dataset.editForm = String(item.id);
        form.noValidate = true;
        form.innerHTML = `
            <div class="field">
                <label for="item-title-${item.id}">${state.config.titleLabel}</label>
                <input
                    id="item-title-${item.id}"
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
                <label for="item-description-${item.id}">${state.config.descriptionLabel}</label>
                <textarea
                    id="item-description-${item.id}"
                    name="description"
                    rows="4"
                    minlength="10"
                    placeholder="${state.config.descriptionPlaceholder}"
                ></textarea>
                <p class="field-error" data-description-error aria-live="polite"></p>
            </div>
            <div class="form-actions">
                <button class="button button--primary" type="submit">Save</button>
                <button class="button button--ghost" type="button" data-edit-cancel>Cancel</button>
            </div>
        `;
        form.querySelector('[name="title"]').value = item.title ?? '';
        form.querySelector('[name="description"]').value = item.description ?? '';
        return form;
    };

    const createItem = (item) => {
        const article = document.createElement('article');
        article.className = 'section-item';
        article.dataset.itemId = String(item.id);
        article.setAttribute('role', 'listitem');

        const row = document.createElement('div');
        row.className = 'section-row';

        const dragHandle = document.createElement('span');
        dragHandle.className = 'section-row__drag-handle';
        dragHandle.setAttribute('aria-hidden', 'true');
        dragHandle.title = 'Drag to reorder';
        dragHandle.innerHTML =
            '<span></span><span></span><span></span><span></span><span></span><span></span>';

        const body = document.createElement('div');
        body.className = 'section-row__body';

        const title = document.createElement('button');
        title.className = 'section-row__title';
        title.type = 'button';
        title.dataset.itemTitle = '';
        title.textContent = item.title ?? `Untitled ${state.config.singularLower}`;
        title.setAttribute('aria-label', `${title.textContent}. Open ${state.config.singularLower}.`);

        const description = document.createElement('p');
        description.className = 'section-row__description';
        description.textContent = item.description ?? 'No description';

        body.append(title, description);

        const menuWrap = document.createElement('div');
        menuWrap.className = 'section-row__menu-wrap';

        const menuButton = document.createElement('button');
        menuButton.className = 'section-row__menu-button';
        menuButton.type = 'button';
        menuButton.dataset.itemMenuTrigger = '';
        menuButton.setAttribute('aria-label', `Open menu for ${title.textContent}`);
        menuButton.setAttribute('aria-haspopup', 'menu');
        menuButton.setAttribute('aria-expanded', 'false');
        menuButton.textContent = '⋮';

        const menu = document.createElement('div');
        menu.className = 'section-row__menu';
        menu.dataset.itemMenu = '';
        menu.setAttribute('role', 'menu');
        menu.hidden = true;
        menu.innerHTML = `
            <button type="button" class="section-row__menu-item" data-item-action="edit" role="menuitem">Edit</button>
            <button type="button" class="section-row__menu-item section-row__menu-item--danger" data-item-action="delete" role="menuitem">Delete</button>
        `;

        menuWrap.append(menuButton, menu);
        row.append(dragHandle, body, menuWrap);
        article.appendChild(row);

        if (state.editingItemId === String(item.id)) {
            article.classList.add('is-editing');
            article.appendChild(createInlineEditor(item));
        }

        return article;
    };

    const renderItems = () => {
        closeActiveMenu();
        state.itemList.innerHTML = '';

        if (state.items.length === 0) {
            state.itemList.innerHTML = `
                <div class="empty-state" role="status">
                    <p class="empty-state__title">${state.config.emptyText}</p>
                </div>
            `;
            return;
        }

        const fragment = document.createDocumentFragment();
        state.items.forEach((item) => fragment.appendChild(createItem(item)));
        state.itemList.appendChild(fragment);

        if (state.editingItemId !== null) {
            state.itemList
                .querySelector(`[data-edit-form="${state.editingItemId}"] [name="title"]`)
                ?.focus();
        }
    };

    const updateItemOrder = async () => {
        const itemElements = [...state.itemList.querySelectorAll('.section-item')];
        const orderedItems = itemElements.map((item, index) => ({
            id: Number(item.dataset.itemId),
            order: index + 1,
        }));

        const response = await fetch(state.config.orderUrl, {
            method: 'PATCH',
            headers: {
                Authorization: `Bearer ${getToken()}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                [state.config.orderPayloadKey]: orderedItems,
            }),
        });

        if (!response.ok) {
            const message = await getBackendErrorMessage(
                response,
                `Failed to update ${state.config.singularLower} order.`
            );
            throw new Error(message);
        }

        const itemsById = new Map(state.items.map((item) => [String(item.id), item]));
        state.items = itemElements
            .map((item) => itemsById.get(item.dataset.itemId))
            .filter(Boolean);
    };

    const initSorting = () => {
        state.sortable = new Sortable(state.itemList, {
            animation: 150,
            draggable: '.section-item',
            handle: '.section-row__drag-handle',
            ghostClass: 'section-item--drag-ghost',
            chosenClass: 'section-item--drag-chosen',
            dragClass: 'section-item--dragging',
            onStart: () => {
                closeActiveMenu();
                document.body.classList.add('is-sorting-sections');
            },
            onEnd: async (event) => {
                document.body.classList.remove('is-sorting-sections');

                if (event.oldIndex === event.newIndex) {
                    return;
                }

                state.sortable.option('disabled', true);

                try {
                    await updateItemOrder();
                    state.sortable.option('disabled', false);
                } catch (error) {
                    showNotification(
                        error.message ||
                            `Failed to update ${state.config.singularLower} order.`,
                        'error'
                    );
                    window.setTimeout(() => window.location.reload(), 1500);
                }
            },
        });
    };

    const openEditor = (itemId) => {
        closeActiveMenu();
        closeCreateForm();
        state.editingItemId = itemId;
        renderItems();
    };

    const deleteItem = async (itemId) => {
        const response = await fetch(state.config.itemUrl(itemId), {
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
            const message = await getBackendErrorMessage(
                response,
                `Failed to delete ${state.config.singularLower}.`
            );
            throw new Error(message);
        }

        state.items = state.items.filter((item) => String(item.id) !== itemId);
        if (state.editingItemId === itemId) {
            state.editingItemId = null;
        }
        renderItems();
        return true;
    };

    const closeDeleteDialog = () => {
        state.deleteDialog.hidden = true;
        state.pendingDeleteItemId = null;
    };

    const showDeleteDialog = (itemId) => {
        state.pendingDeleteItemId = itemId;
        state.deleteDialog.querySelector('[data-delete-dialog-title]').textContent =
            `Delete this ${state.config.singularLower}?`;
        state.deleteDialog.hidden = false;
        state.deleteDialog.querySelector('[data-delete-cancel]')?.focus();
    };

    const buildDeleteDialog = () => {
        const overlay = document.createElement('div');
        overlay.className = 'dialog-overlay';
        overlay.hidden = true;
        overlay.innerHTML = `
            <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="delete-item-title" aria-describedby="delete-item-description">
                <h2 id="delete-item-title" data-delete-dialog-title></h2>
                <p id="delete-item-description">This action cannot be undone.</p>
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
            const itemId = state.pendingDeleteItemId;

            if (!itemId) {
                closeDeleteDialog();
                return;
            }

            confirmButton.disabled = true;
            cancelButton.disabled = true;

            try {
                const deleted = await deleteItem(itemId);
                closeDeleteDialog();
                if (deleted) {
                    showNotification(`${state.config.singular} deleted.`, 'success');
                }
            } catch (error) {
                closeDeleteDialog();
                showNotification(
                    error.message || `Failed to delete ${state.config.singularLower}.`,
                    'error'
                );
            } finally {
                confirmButton.disabled = false;
                cancelButton.disabled = false;
            }
        });
    };

    const handleItemListClick = (event) => {
        const menuTrigger = event.target.closest('[data-item-menu-trigger]');
        if (menuTrigger) {
            toggleMenu(menuTrigger.closest('.section-item'));
            return;
        }

        const actionButton = event.target.closest('[data-item-action]');
        if (actionButton) {
            const itemId = actionButton.closest('.section-item')?.dataset.itemId;
            const action = actionButton.dataset.itemAction;

            closeActiveMenu();
            if (!itemId) {
                return;
            }

            if (action === 'edit') {
                openEditor(itemId);
            } else if (action === 'delete') {
                showDeleteDialog(itemId);
            }
            return;
        }

        if (event.target.closest('[data-edit-cancel]')) {
            closeEditor();
            return;
        }

        const itemTitle = event.target.closest('[data-item-title]');
        if (itemTitle) {
            const itemId = itemTitle.closest('.section-item')?.dataset.itemId;
            if (itemId) {
                window.location.href = state.config.itemDestination(itemId);
            }
            return;
        }

        const itemRow = event.target.closest('.section-row');
        if (
            state.config.kind === 'lesson' &&
            itemRow &&
            !event.target.closest('.section-row__drag-handle')
        ) {
            const itemId = itemRow.closest('.section-item')?.dataset.itemId;
            if (itemId) {
                window.location.href = state.config.itemDestination(itemId);
            }
        }
    };

    const handleEditSubmit = async (event) => {
        const form = event.target.closest('[data-edit-form]');
        if (!form) {
            return;
        }

        event.preventDefault();
        const values = validateItemForm(form);
        if (!values) {
            return;
        }

        const itemId = form.dataset.editForm;
        const submitButton = form.querySelector('[type="submit"]');
        const cancelButton = form.querySelector('[data-edit-cancel]');
        submitButton.disabled = true;
        cancelButton.disabled = true;
        submitButton.textContent = 'Saving...';

        try {
            const response = await fetch(state.config.itemUrl(itemId), {
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
                const message = await getBackendErrorMessage(
                    response,
                    `Failed to update ${state.config.singularLower}.`
                );
                throw new Error(message);
            }

            const updatedItem = await response.json();
            state.items = state.items.map((item) =>
                String(item.id) === itemId ? updatedItem : item
            );
            state.editingItemId = null;
            renderItems();
            showNotification(`${state.config.singular} updated.`, 'success');
        } catch (error) {
            showNotification(
                error.message || `Failed to update ${state.config.singularLower}.`,
                'error'
            );
        } finally {
            submitButton.disabled = false;
            cancelButton.disabled = false;
            submitButton.textContent = 'Save';
        }
    };

    const handleCreateSubmit = async (event) => {
        event.preventDefault();
        const values = validateItemForm(state.createForm);
        if (!values) {
            return;
        }

        const submitButton = state.createForm.querySelector('[data-create-submit]');
        const cancelButton = state.createForm.querySelector('[data-create-cancel]');
        submitButton.disabled = true;
        cancelButton.disabled = true;
        submitButton.textContent = 'Creating...';

        try {
            const response = await fetch(state.config.createUrl, {
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
                const message = await getBackendErrorMessage(
                    response,
                    `Failed to create ${state.config.singularLower}.`
                );
                throw new Error(message);
            }

            const item = await response.json();
            state.items.push(item);
            closeCreateForm();
            renderItems();
            showNotification(`${state.config.singular} created.`, 'success');
        } catch (error) {
            showNotification(
                error.message || `Failed to create ${state.config.singularLower}.`,
                'error'
            );
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

    const applyViewText = () => {
        state.backLink.href = state.config.backUrl;
        state.backLink.textContent = state.config.backText;
        state.listTitle.textContent = state.config.listTitle;
        state.newItemButton.textContent = state.config.newButtonText;
        state.createForm.querySelector('[data-form-title-label]').textContent =
            state.config.titleLabel;
        state.createForm.querySelector('[data-form-description-label]').textContent =
            state.config.descriptionLabel;
        state.createForm.querySelector('[name="description"]').placeholder =
            state.config.descriptionPlaceholder;
    };

    const loadStructure = async () => {
        showLoading(state.config.parentLoadingText);
        const headers = {
            Authorization: `Bearer ${getToken()}`,
        };

        const [parentResponse, itemsResponse] = await Promise.all([
            fetch(state.config.parentUrl, { headers }),
            fetch(state.config.itemsUrl, { headers }),
        ]);

        if (parentResponse.status === 401 || itemsResponse.status === 401) {
            clearToken();
            redirectHome();
            return;
        }

        if (!parentResponse.ok) {
            const message = await getBackendErrorMessage(
                parentResponse,
                `Failed to load ${state.config.kind === 'lesson' ? 'section' : 'course'}.`
            );
            throw new Error(message);
        }

        if (!itemsResponse.ok) {
            const message = await getBackendErrorMessage(
                itemsResponse,
                `Failed to load ${state.config.pluralLower}.`
            );
            throw new Error(message);
        }

        const [parent, items] = await Promise.all([
            parentResponse.json(),
            itemsResponse.json(),
        ]);

        state.structureTitle.textContent = parent.title ?? state.config.parentFallback;
        document.title = `${state.structureTitle.textContent} — ${state.config.pageSuffix}`;
        state.items = Array.isArray(items) ? items : [];
        renderItems();
        showContent();
    };

    const handleDocumentClick = (event) => {
        if (
            state.activeMenu &&
            !event.target.closest('[data-item-menu]') &&
            !event.target.closest('[data-item-menu-trigger]')
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
        } else if (state.editingItemId !== null) {
            closeEditor();
        } else if (!state.createForm.hidden) {
            closeCreateForm();
        }
    };

    const init = async () => {
        state.loading = document.querySelector('[data-admin-loading]');
        state.error = document.querySelector('[data-admin-error]');
        state.content = document.querySelector('[data-admin-content]');
        state.structureTitle = document.querySelector('[data-structure-title]');
        state.listTitle = document.querySelector('[data-list-title]');
        state.itemList = document.querySelector('[data-item-list]');
        state.notification = document.querySelector('[data-admin-notifications]');
        state.backLink = document.querySelector('[data-structure-back]');
        state.newItemButton = document.querySelector('[data-new-item]');
        state.createForm = document.querySelector('[data-create-form]');
        state.courseId = getCourseId();
        state.sectionId = getSectionId();

        if (!state.courseId) {
            showError('Invalid course ID.');
            return;
        }

        state.config = createConfig();
        applyViewText();
        buildDeleteDialog();
        initSorting();
        state.itemList.addEventListener('click', handleItemListClick);
        state.itemList.addEventListener('submit', handleEditSubmit);
        state.newItemButton.addEventListener('click', openCreateForm);
        state.createForm.addEventListener('submit', handleCreateSubmit);
        state.createForm
            .querySelector('[data-create-cancel]')
            .addEventListener('click', closeCreateForm);
        document.addEventListener('click', handleDocumentClick);
        document.addEventListener('keydown', handleKeydown);

        try {
            const hasAccess = await checkAdminAccess();
            if (hasAccess) {
                await loadStructure();
            }
        } catch (error) {
            showError(
                error.message ||
                    `Failed to load ${state.config.kind === 'lesson' ? 'lessons' : 'course structure'}.`
            );
        }
    };

    document.addEventListener('DOMContentLoaded', init);
})();
