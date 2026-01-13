(function () {
  const year = new Date().getFullYear();
  const el = document.querySelector('[data-year]');
  if (el) el.textContent = year;

  // Basic outbound click tracking hook (no analytics by default).
  // If you add analytics later, attach here.
})();
