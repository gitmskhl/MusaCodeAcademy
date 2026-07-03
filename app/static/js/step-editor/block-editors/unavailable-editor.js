export const renderUnavailableEditor = ({ label }) => {
    const editor = document.createElement('div');
    editor.className = 'block-properties__unavailable';
    editor.innerHTML = `
        <span class="block-properties__unavailable-icon" aria-hidden="true">◇</span>
        <p>${label} block editing is not implemented yet.</p>
    `;
    return editor;
};
