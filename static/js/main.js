// main.js — students will add JavaScript here as features are built

// Ask for confirmation before any element marked data-confirm acts.
// Delegated on document so it works for any page without per-element listeners.
document.addEventListener("click", function (event) {
    var target = event.target.closest("[data-confirm]");
    if (target && !window.confirm(target.dataset.confirm)) {
        event.preventDefault();
    }
});
