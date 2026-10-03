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

  // Build-time dates remain readable without JS. Hide expired listings in
  // long-lived tabs or if deployment refreshes stop; HamStudy remains authoritative.
  function expireSchedule() {
    const schedule = document.querySelector("[data-session-schedule]");
    if (!schedule) return;
    const stale = Date.now() >= Number(schedule.dataset.expiresAt);
    let visible = 0;
    schedule.querySelectorAll("[data-session-start]").forEach(row => {
      row.hidden = stale || Date.now() >= Number(row.dataset.sessionStart);
      if (!row.hidden) visible++;
    });
    const list = schedule.querySelector("[data-session-list]");
    if (list) list.hidden = visible === 0;
    const fallback = schedule.querySelector("[data-session-fallback]");
    if (fallback) fallback.hidden = visible > 0;
    const checked = schedule.querySelector("[data-session-checked]");
    if (checked) checked.hidden = stale;
  }
  expireSchedule();
  if (document.querySelector("[data-session-schedule]")) {
    setInterval(expireSchedule, 60000);
    document.addEventListener("visibilitychange", expireSchedule);
  }
})();
