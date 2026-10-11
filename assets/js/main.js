(function () {
  if (document.querySelector("pagefind-searchbox")) {
      if (!document.querySelector('link[data-pagefind-component]')) {
        const pagefindStyles = document.createElement("link");
        pagefindStyles.rel = "stylesheet";
        pagefindStyles.href = "/pagefind/pagefind-component-ui.css";
        pagefindStyles.dataset.pagefindComponent = "";
        document.head.appendChild(pagefindStyles);
      }

      if (!document.querySelector('script[data-pagefind-component]')) {
        const pagefindScript = document.createElement("script");
        pagefindScript.type = "module";
        pagefindScript.src = "/pagefind/pagefind-component-ui.js";
        pagefindScript.dataset.pagefindComponent = "";
        document.head.appendChild(pagefindScript);
      }
  }
  const year = document.querySelector("[data-year]");
  if (year) year.textContent = new Date().getFullYear();

  // A delayed build should show a freshness notice, not erase future dates.
  // Hide started sessions immediately and discard snapshots after 48 hours.
  function expireSchedule() {
    const schedule = document.querySelector("[data-session-schedule]");
    if (!schedule) return;
    const now = Date.now();
    const expiresAt = Number(schedule.dataset.expiresAt);
    const stale = !Number.isFinite(expiresAt) || now >= expiresAt;
    const requestedLimit = Number(schedule.dataset.sessionLimit);
    const displayLimit = Number.isInteger(requestedLimit) && requestedLimit > 0
      ? requestedLimit : Infinity;
    let visible = 0;
    schedule.querySelectorAll("[data-session-start]").forEach(row => {
      const start = Number(row.dataset.sessionStart);
      const rowExpiry = row.dataset.sessionExpiresAt
        ? Number(row.dataset.sessionExpiresAt) : expiresAt;
      const eligible = Number.isFinite(rowExpiry) && now < rowExpiry &&
        Number.isFinite(start) && now < start;
      row.hidden = !eligible || visible >= displayLimit;
      if (!row.hidden) visible++;
    });
    const list = schedule.querySelector("[data-session-list]");
    if (list) list.hidden = visible === 0;
    const fallback = schedule.querySelector("[data-session-fallback]");
    if (fallback) fallback.hidden = visible > 0;
    const checked = schedule.querySelector("[data-session-checked]");
    if (checked) checked.hidden = stale;
    const warning = schedule.querySelector("[data-session-stale-warning]");
    if (warning) warning.hidden = stale || now < Number(schedule.dataset.freshUntil);
  }
  expireSchedule();
  if (document.querySelector("[data-session-schedule]")) {
    setInterval(expireSchedule, 60000);
    document.addEventListener("visibilitychange", expireSchedule);
  }
})();
