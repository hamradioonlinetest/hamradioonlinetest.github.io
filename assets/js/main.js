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

  // HamStudy provides absolute UTC instants. Server-rendered HTML stays explicitly
  // labelled Eastern Time for visitors without JavaScript; browsers convert only
  // after establishing a real IANA time zone from the visitor's device.
  function localizeSchedules() {
    if (!document.querySelector("[data-session-schedule]")) return;
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (!zone) return; // Keep the clearly labelled Eastern fallback.
    try {
      const dateFormat = new Intl.DateTimeFormat(undefined, {
        timeZone: zone, weekday: "long", year: "numeric", month: "long", day: "numeric"
      });
      const shortDate = new Intl.DateTimeFormat(undefined, {
        timeZone: zone, month: "short", day: "numeric"
      });
      const clockFormat = new Intl.DateTimeFormat(undefined, {
        timeZone: zone, hour: "numeric", minute: "2-digit"
      });
      const zoneFormat = new Intl.DateTimeFormat("en-US", {
        timeZone: zone, hour: "numeric", timeZoneName: "short"
      });
      const abbreviation = date => zoneFormat.formatToParts(date)
        .find(part => part.type === "timeZoneName")?.value || zone;
      const displayTime = date => clockFormat.format(date);
      const notes = typeof document.querySelectorAll === "function"
        ? document.querySelectorAll("[data-session-timezone-label]") : [];
      // Avoid calling a fixed present-day PDT/EST offset a future session's offset:
      // each appointment has its own date-specific zone abbreviation.
      notes.forEach(node => {
        node.textContent = "Times shown in your device's time zone: " + zone + ".";
      });
      document.querySelectorAll("[data-session-schedule]").forEach(schedule => {
        schedule.querySelectorAll("[data-session-start]").forEach(row => {
          if (typeof row.querySelector !== "function") return;
          const startMs = Number(row.dataset.sessionStart);
          const endMs = Number(row.dataset.sessionEnd);
          if (!Number.isSafeInteger(startMs) || !Number.isSafeInteger(endMs) ||
              endMs <= startMs) return; // Preserve Eastern fallback on bad data.
          const start = new Date(startMs), end = new Date(endMs);
          if (!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime())) return;
          const dateNode = row.querySelector("time");
          const clockNode = row.querySelector(".session-clock");
          if (!dateNode || !clockNode) return;
          const dateText = dateFormat.format(start);
          const endDateText = dateFormat.format(end);
          const a = abbreviation(start), b = abbreviation(end);
          let clockText = a === b
            ? displayTime(start) + "–" + displayTime(end) + " " + b
            : displayTime(start) + " " + a + " – " + displayTime(end) + " " + b;
          if (dateText !== endDateText) {
            clockText += " (ends " + shortDate.format(end) + ")";
          }
          dateNode.textContent = dateText;
          dateNode.dateTime = start.toISOString();
          clockNode.textContent = clockText;
          const link = row.querySelector("a[aria-label]");
          if (link) {
            const vec = row.querySelector(".session-vec")?.textContent.split(" · ")[0];
            link.setAttribute("aria-label",
              (vec ? "Register with " + vec : "View session") +
              " on " + dateText + " at " + clockText);
          }
        });
        schedule.querySelectorAll("[data-session-checked-at]").forEach(node => {
          const ms = Number(node.dataset.sessionCheckedAt);
          if (!Number.isSafeInteger(ms) || typeof node.textContent !== "string") return;
          const d = new Date(ms);
          node.textContent = (node.dataset.sessionCheckedVec
            ? node.dataset.sessionCheckedVec + ": " : "") +
            shortDate.format(d) + " at " + displayTime(d) + " " + abbreviation(d);
        });
      });
    } catch (err) {
      // Unsupported/invalid browser time zone: retain Eastern-labelled SSR.
      // Avoid replacing any visible content when creating the formatters fails.
    }
  }
  localizeSchedules();

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
