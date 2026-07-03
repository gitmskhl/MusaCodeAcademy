(function () {
    const TOKEN_KEY = 'musa_code_academy_token';
    const DEFAULT_STEP_CONTENT = {
        version: 1,
        layout: 'vertical',
        blocks: [],
    };

    const state = {
        lessonId: null,
        steps: [],
        activeMenu: null,
        editingStepId: null,
        pendingDeleteStepId: null,
        deleteDialog: null,
        notificationTimer: null,
        sortable: null,
        isSorting: false,
        loading: null,
        error: null,
        content: null,
        title: null,
        backLink: null,
        stepList: null,
        notification: null,
        newStepButton: null,
        createForm: null,
    };

    const getToken = () => localStorage.getItem(TOKEN_KEY);

    const clearToken = () => localStorage.removeItem(TOKEN_KEY);

    const redirectHome = () => {
        window.location.href = '/';
    };

    const getLessonId = () => {
        const value = state.content?.dataset.lessonId;
        return value && /^\d+$/.test(value) ? value : null;
    };

    const getStepUrl = (stepId) => `/api/steps/${encodeURIComponent(stepId)}/admin`;

    const getStepDestination = (stepId) =>
        `/admin/steps/${encodeURIComponent(stepId)}`;

    const getBackendErrorMessage = async (response, fallbackMessage) => {
        const responseCopy = response.clone();

        try {
            const data = await response.json();
            return typeof data?.detail === 'string'
                ? data.detail
                : data?.message || fallbackMessage;
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
        state.activeMenu.step.classList.remove('is-menu-open');
        state.activeMenu = null;
    };

    const toggleMenu = (stepElement) => {
        const trigger = stepElement.querySelector('[data-step-menu-trigger]');
        const menu = stepElement.querySelector('[data-step-menu]');

        if (!trigger || !menu) {
            return;
        }

        if (state.activeMenu?.step === stepElement) {
            closeActiveMenu();
            return;
        }

        closeActiveMenu();
        trigger.setAttribute('aria-expanded', 'true');
        menu.hidden = false;
        stepElement.classList.add('is-menu-open');
        state.activeMenu = { step: stepElement, trigger, menu };
    };

    const clearTitleError = (form) => {
        form.querySelector('[name="title"]')?.removeAttribute('aria-invalid');
        form.querySelector('[data-title-error]').textContent = '';
    };

    const closeCreateForm = () => {
        state.createForm.hidden = true;
        state.createForm.reset();
        clearTitleError(state.createForm);
        state.newStepButton.hidden = false;
    };

    const closeEditor = () => {
        if (state.editingStepId === null) {
            return;
        }

        state.editingStepId = null;
        renderSteps();
    };

    const openCreateForm = () => {
        closeActiveMenu();
        closeEditor();
        state.newStepButton.hidden = true;
        state.createForm.hidden = false;
        state.createForm.querySelector('[name="title"]')?.focus();
    };

    const validateTitle = (form) => {
        const titleInput = form.querySelector('[name="title"]');
        const titleError = form.querySelector('[data-title-error]');
        const title = titleInput?.value.trim() ?? '';
        let message = '';

        if (!title) {
            message = 'Step title is required.';
        } else if (title.length > 255) {
            message = 'Step title must contain no more than 255 characters.';
        }

        titleInput?.toggleAttribute('aria-invalid', Boolean(message));
        titleError.textContent = message;

        if (message) {
            titleInput?.focus();
            return null;
        }

        return title;
    };

    const createInlineEditor = (step) => {
        const form = document.createElement('form');
        form.className = 'inline-section-form inline-section-form--edit';
        form.dataset.editForm = String(step.id);
        form.noValidate = true;
        form.innerHTML = `
            <div class="field">
                <label for="step-title-${step.id}">Step title</label>
                <input
                    id="step-title-${step.id}"
                    name="title"
                    type="text"
                    minlength="1"
                    maxlength="255"
                    autocomplete="off"
                    required
                >
                <p class="field-error" data-title-error aria-live="polite"></p>
            </div>
            <div class="form-actions">
                <button class="button button--primary" type="submit">Save</button>
                <button class="button button--ghost" type="button" data-edit-cancel>Cancel</button>
            </div>
        `;
        form.querySelector('[name="title"]').value = step.title ?? '';
        return form;
    };

    const createStepElement = (step) => {
        const article = document.createElement('article');
        article.className = 'section-item';
        article.dataset.stepId = String(step.id);
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
        title.dataset.stepTitle = '';
        title.textContent = step.title ?? 'Untitled step';
        title.setAttribute('aria-label', `${title.textContent}. Open step.`);
        body.appendChild(title);

        const menuWrap = document.createElement('div');
        menuWrap.className = 'section-row__menu-wrap';

        const menuButton = document.createElement('button');
        menuButton.className = 'section-row__menu-button';
        menuButton.type = 'button';
        menuButton.dataset.stepMenuTrigger = '';
        menuButton.setAttribute('aria-label', `Open menu for ${title.textContent}`);
        menuButton.setAttribute('aria-haspopup', 'menu');
        menuButton.setAttribute('aria-expanded', 'false');
        menuButton.textContent = '⋮';

        const menu = document.createElement('div');
        menu.className = 'section-row__menu';
        menu.dataset.stepMenu = '';
        menu.setAttribute('role', 'menu');
        menu.hidden = true;
        menu.innerHTML = `
            <button type="button" class="section-row__menu-item" data-step-action="edit" role="menuitem">Edit</button>
            <button type="button" class="section-row__menu-item section-row__menu-item--danger" data-step-action="delete" role="menuitem">Delete</button>
        `;

        menuWrap.append(menuButton, menu);
        row.append(dragHandle, body, menuWrap);
        article.appendChild(row);

        if (state.editingStepId === String(step.id)) {
            article.classList.add('is-editing');
            article.appendChild(createInlineEditor(step));
        }

        return article;
    };

    const renderSteps = () => {
        closeActiveMenu();
        state.stepList.innerHTML = '';

        if (state.steps.length === 0) {
            state.stepList.innerHTML = `
                <div class="empty-state" role="status">
                    <p class="empty-state__title">No steps yet</p>
                </div>
            `;
            return;
        }

        const fragment = document.createDocumentFragment();
        state.steps.forEach((step) => fragment.appendChild(createStepElement(step)));
        state.stepList.appendChild(fragment);

        if (state.editingStepId !== null) {
            state.stepList
                .querySelector(`[data-edit-form="${state.editingStepId}"] [name="title"]`)
                ?.focus();
        }
    };

    const updateStepOrder = async () => {
        const stepElements = [...state.stepList.querySelectorAll('.section-item')];
        const orderedSteps = stepElements.map((step, index) => ({
            id: Number(step.dataset.stepId),
            order: index + 1,
        }));

        const response = await fetch('/api/steps/admin/order', {
            method: 'PATCH',
            headers: {
                Authorization: `Bearer ${getToken()}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ steps: orderedSteps }),
        });

        if (response.status === 401) {
            clearToken();
            redirectHome();
            return false;
        }

        if (!response.ok) {
            const message = await getBackendErrorMessage(
                response,
                'Failed to update step order.'
            );
            throw new Error(message);
        }

        const stepsById = new Map(state.steps.map((step) => [String(step.id), step]));
        state.steps = stepElements
            .map((step) => stepsById.get(step.dataset.stepId))
            .filter(Boolean);
        return true;
    };

    const initSorting = () => {
        state.sortable = new Sortable(state.stepList, {
            animation: 150,
            draggable: '.section-item',
            handle: '.section-row__drag-handle',
            ghostClass: 'section-item--drag-ghost',
            chosenClass: 'section-item--drag-chosen',
            dragClass: 'section-item--dragging',
            onStart: () => {
                state.isSorting = true;
                closeActiveMenu();
                document.body.classList.add('is-sorting-sections');
            },
            onEnd: async (event) => {
                document.body.classList.remove('is-sorting-sections');
                window.setTimeout(() => {
                    state.isSorting = false;
                }, 0);

                if (event.oldIndex === event.newIndex) {
                    return;
                }

                state.sortable.option('disabled', true);

                try {
                    const updated = await updateStepOrder();
                    if (updated) {
                        state.sortable.option('disabled', false);
                    }
                } catch (error) {
                    showNotification(error.message || 'Failed to update step order.', 'error');
                    window.setTimeout(() => window.location.reload(), 1500);
                }
            },
        });
    };

    const openEditor = (stepId) => {
        closeActiveMenu();
        closeCreateForm();
        state.editingStepId = stepId;
        renderSteps();
    };

    const deleteStep = async (stepId) => {
        const response = await fetch(getStepUrl(stepId), {
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
            const message = await getBackendErrorMessage(response, 'Failed to delete step.');
            throw new Error(message);
        }

        state.steps = state.steps.filter((step) => String(step.id) !== stepId);
        if (state.editingStepId === stepId) {
            state.editingStepId = null;
        }
        renderSteps();
        return true;
    };

    const closeDeleteDialog = () => {
        state.deleteDialog.hidden = true;
        state.pendingDeleteStepId = null;
    };

    const showDeleteDialog = (stepId) => {
        state.pendingDeleteStepId = stepId;
        state.deleteDialog.hidden = false;
        state.deleteDialog.querySelector('[data-delete-cancel]')?.focus();
    };

    const buildDeleteDialog = () => {
        const overlay = document.createElement('div');
        overlay.className = 'dialog-overlay';
        overlay.hidden = true;
        overlay.innerHTML = `
            <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="delete-step-title" aria-describedby="delete-step-description">
                <h2 id="delete-step-title">Delete this step?</h2>
                <p id="delete-step-description">This action cannot be undone.</p>
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
            const stepId = state.pendingDeleteStepId;

            if (!stepId) {
                closeDeleteDialog();
                return;
            }

            confirmButton.disabled = true;
            cancelButton.disabled = true;

            try {
                const deleted = await deleteStep(stepId);
                closeDeleteDialog();
                if (deleted) {
                    showNotification('Step deleted.', 'success');
                }
            } catch (error) {
                closeDeleteDialog();
                showNotification(error.message || 'Failed to delete step.', 'error');
            } finally {
                confirmButton.disabled = false;
                cancelButton.disabled = false;
            }
        });
    };

    const handleStepListClick = (event) => {
        const menuTrigger = event.target.closest('[data-step-menu-trigger]');
        if (menuTrigger) {
            toggleMenu(menuTrigger.closest('.section-item'));
            return;
        }

        const actionButton = event.target.closest('[data-step-action]');
        if (actionButton) {
            const stepId = actionButton.closest('.section-item')?.dataset.stepId;
            const action = actionButton.dataset.stepAction;

            closeActiveMenu();
            if (!stepId) {
                return;
            }

            if (action === 'edit') {
                openEditor(stepId);
            } else if (action === 'delete') {
                showDeleteDialog(stepId);
            }
            return;
        }

        if (event.target.closest('[data-edit-cancel]')) {
            closeEditor();
            return;
        }

        const stepRow = event.target.closest('.section-row');
        if (
            stepRow &&
            !state.isSorting &&
            !event.target.closest('.section-row__drag-handle')
        ) {
            const stepId = stepRow.closest('.section-item')?.dataset.stepId;
            if (stepId) {
                window.location.href = getStepDestination(stepId);
            }
        }
    };

    const handleEditSubmit = async (event) => {
        const form = event.target.closest('[data-edit-form]');
        if (!form) {
            return;
        }

        event.preventDefault();
        const title = validateTitle(form);
        if (!title) {
            return;
        }

        const stepId = form.dataset.editForm;
        const submitButton = form.querySelector('[type="submit"]');
        const cancelButton = form.querySelector('[data-edit-cancel]');
        submitButton.disabled = true;
        cancelButton.disabled = true;
        submitButton.textContent = 'Saving...';

        try {
            const response = await fetch(getStepUrl(stepId), {
                method: 'PATCH',
                headers: {
                    Authorization: `Bearer ${getToken()}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ title }),
            });

            if (response.status === 401) {
                clearToken();
                redirectHome();
                return;
            }

            if (!response.ok) {
                const message = await getBackendErrorMessage(
                    response,
                    'Failed to update step.'
                );
                throw new Error(message);
            }

            const updatedStep = await response.json();
            state.steps = state.steps.map((step) =>
                String(step.id) === stepId ? updatedStep : step
            );
            state.editingStepId = null;
            renderSteps();
            showNotification('Step updated.', 'success');
        } catch (error) {
            showNotification(error.message || 'Failed to update step.', 'error');
        } finally {
            submitButton.disabled = false;
            cancelButton.disabled = false;
            submitButton.textContent = 'Save';
        }
    };

    const handleCreateSubmit = async (event) => {
        event.preventDefault();
        const title = validateTitle(state.createForm);
        if (!title) {
            return;
        }

        const submitButton = state.createForm.querySelector('[data-create-submit]');
        const cancelButton = state.createForm.querySelector('[data-create-cancel]');
        submitButton.disabled = true;
        cancelButton.disabled = true;
        submitButton.textContent = 'Creating...';

        try {
            const response = await fetch(
                `/api/lessons/${encodeURIComponent(state.lessonId)}/steps/admin`,
                {
                    method: 'POST',
                    headers: {
                        Authorization: `Bearer ${getToken()}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        title,
                        content: DEFAULT_STEP_CONTENT,
                    }),
                }
            );

            if (response.status === 401) {
                clearToken();
                redirectHome();
                return;
            }

            if (!response.ok) {
                const message = await getBackendErrorMessage(
                    response,
                    'Failed to create step.'
                );
                throw new Error(message);
            }

            const step = await response.json();
            state.steps.push(step);
            closeCreateForm();
            renderSteps();
            showNotification('Step created.', 'success');
        } catch (error) {
            showNotification(error.message || 'Failed to create step.', 'error');
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

    const setBackLink = async (lesson) => {
        try {
            const response = await fetch(`/api/sections/${lesson.section_id}/admin`, {
                headers: {
                    Authorization: `Bearer ${getToken()}`,
                },
            });

            if (response.status === 401) {
                clearToken();
                redirectHome();
                return;
            }

            if (!response.ok) {
                return;
            }

            const section = await response.json();
            state.backLink.href =
                `/admin/courses/${encodeURIComponent(section.course_id)}` +
                `?section=${encodeURIComponent(lesson.section_id)}`;
        } catch {
            // The Step list remains usable with the fallback Admin link.
        }
    };

    const loadSteps = async () => {
        showLoading('Loading lesson...');
        const headers = {
            Authorization: `Bearer ${getToken()}`,
        };
        const lessonUrl = `/api/lessons/${encodeURIComponent(state.lessonId)}/admin`;
        const stepsUrl =
            `/api/lessons/${encodeURIComponent(state.lessonId)}/steps/admin`;

        const [lessonResponse, stepsResponse] = await Promise.all([
            fetch(lessonUrl, { headers }),
            fetch(stepsUrl, { headers }),
        ]);

        if (lessonResponse.status === 401 || stepsResponse.status === 401) {
            clearToken();
            redirectHome();
            return;
        }

        if (!lessonResponse.ok) {
            const message = await getBackendErrorMessage(
                lessonResponse,
                'Failed to load lesson.'
            );
            throw new Error(message);
        }

        if (!stepsResponse.ok) {
            const message = await getBackendErrorMessage(
                stepsResponse,
                'Failed to load steps.'
            );
            throw new Error(message);
        }

        const [lesson, steps] = await Promise.all([
            lessonResponse.json(),
            stepsResponse.json(),
        ]);

        state.title.textContent = lesson.title ?? 'Untitled lesson';
        document.title = `${state.title.textContent} — Steps`;
        state.steps = Array.isArray(steps) ? steps : [];
        renderSteps();
        showContent();
        await setBackLink(lesson);
    };

    const handleDocumentClick = (event) => {
        if (
            state.activeMenu &&
            !event.target.closest('[data-step-menu]') &&
            !event.target.closest('[data-step-menu-trigger]')
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
        } else if (state.editingStepId !== null) {
            closeEditor();
        } else if (!state.createForm.hidden) {
            closeCreateForm();
        }
    };

    const init = async () => {
        state.loading = document.querySelector('[data-admin-loading]');
        state.error = document.querySelector('[data-admin-error]');
        state.content = document.querySelector('[data-admin-content]');
        state.title = document.querySelector('[data-steps-title]');
        state.backLink = document.querySelector('[data-steps-back]');
        state.stepList = document.querySelector('[data-step-list]');
        state.notification = document.querySelector('[data-admin-notifications]');
        state.newStepButton = document.querySelector('[data-new-step]');
        state.createForm = document.querySelector('[data-create-form]');
        state.lessonId = getLessonId();

        if (!state.lessonId) {
            showError('Invalid lesson ID.');
            return;
        }

        buildDeleteDialog();
        initSorting();
        state.stepList.addEventListener('click', handleStepListClick);
        state.stepList.addEventListener('submit', handleEditSubmit);
        state.newStepButton.addEventListener('click', openCreateForm);
        state.createForm.addEventListener('submit', handleCreateSubmit);
        state.createForm
            .querySelector('[data-create-cancel]')
            .addEventListener('click', closeCreateForm);
        document.addEventListener('click', handleDocumentClick);
        document.addEventListener('keydown', handleKeydown);

        try {
            const hasAccess = await checkAdminAccess();
            if (hasAccess) {
                await loadSteps();
            }
        } catch (error) {
            showError(error.message || 'Failed to load lesson steps.');
        }
    };

    document.addEventListener('DOMContentLoaded', init);
})();
