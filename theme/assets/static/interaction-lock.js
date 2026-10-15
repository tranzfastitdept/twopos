(() => {
  document.addEventListener("contextmenu", (event) => event.preventDefault());
  document.addEventListener("dragstart", (event) => event.preventDefault());
  document.addEventListener("selectstart", (event) => {
    if (!event.target.closest("input, textarea")) event.preventDefault();
  });
  document.addEventListener("gesturestart", (event) => event.preventDefault());
  document.addEventListener("wheel", (event) => {
    if (event.ctrlKey || event.metaKey) event.preventDefault();
  }, { passive: false });
  document.addEventListener("keydown", (event) => {
    if (!(event.ctrlKey || event.metaKey)) return;
    if (["+", "-", "=", "_", "0"].includes(event.key)) event.preventDefault();
  });
})();
