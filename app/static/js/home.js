const runButton = document.querySelector('[data-run-demo]');
const output = document.querySelector('[data-demo-output]');

runButton?.addEventListener('click', () => {
    // Preview one iteration of the illustrative Python loop; no user code is executed.
    output.textContent = '› Я могу больше!';
    output.classList.add('is-success');
    runButton.textContent = '✓ Ещё раз';
});
