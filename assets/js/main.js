(function () {
  const searchExcludedPaths = ["/counts/", "/sessions/", "/vescript/"];
  const searchEnabled = !document.title.startsWith("Page not found") &&
    !searchExcludedPaths.includes(window.location.pathname);
  const siteHeader = `
  <header class="header">
    <div class="container">
      <div class="nav">
        <a class="brand" href="https://hamradioonlinetest.com/">
          <img src="https://hamradioonlinetest.com/assets/img/wearc-logo.png" alt="WEARC logo">
          <div>
            <div class="brand-name">West Essex Amateur Radio Club</div>
            <div class="tag">Online exam sessions and new ham support</div>
          </div>
        </a>
        <nav class="navlinks" aria-label="Site">
          <a href="https://hamradioonlinetest.com/online-ham-radio-exam-checklist/">Pre-exam Checklist</a>
          <a href="https://hamradioonlinetest.com/payment/">Payment</a>
          <a href="https://hamradioonlinetest.com/frn/">Check Application Status</a>
          <a href="https://www.wearc.org/" target="_blank" rel="noopener">WEARC Club</a>
          <a class="cta" href="https://hamstudy.org/sessions/WEARC/all" target="_blank" rel="noopener">Find a session</a>
        </nav>
      </div>
      ${searchEnabled ? `<div class="site-search" data-pagefind-ignore>
        <div id="site-search" role="search" aria-label="Search this site"></div>
      </div>` : ""}
    </div>
  </header>`;

  const siteFooter = `
  <footer class="footer">
    <div class="container">
      <div class="card pad">
        <div class="cols">
          <div>
            <div class="kicker">Contact</div>
            <p class="notice">Email: <a href="mailto:hamradiotest@osi3.net">hamradiotest@osi3.net</a><br>
            Call or text: <a href="tel:+1-917-502-2203">+1-917-502-2203</a></p>
          </div>
          <div>
            <div class="kicker">Register</div>
            <p class="notice">Browse dates and register through HamStudy:</p>
            <p><a class="cta" href="https://hamstudy.org/sessions/WEARC/all" target="_blank" rel="noopener">hamstudy.org/sessions/WEARC/all</a></p>
          </div>
          <div>
            <div class="kicker">About WEARC</div>
            <p class="notice">WEARC is based in Essex County, New Jersey. Visitors are welcome at our weekly Zoom club meetings and community nets.</p>
          </div>
        </div>
        <hr class="sep">
        <small>© <span data-year></span> West Essex Amateur Radio Club</small>
      </div>
    </div>
  </footer>`;

  const headerMount = document.querySelector("[data-site-header]");
  if (headerMount) {
    headerMount.outerHTML = siteHeader;

    if (searchEnabled) {
      const pagefindStyles = document.createElement("link");
      pagefindStyles.rel = "stylesheet";
      pagefindStyles.href = "/pagefind/pagefind-ui.css";
      document.head.appendChild(pagefindStyles);

      const pagefindScript = document.createElement("script");
      pagefindScript.src = "/pagefind/pagefind-ui.js";
      pagefindScript.onload = function () {
        const search = document.querySelector("#site-search");
        if (!search || typeof window.PagefindUI !== "function") return;

        new window.PagefindUI({
          element: "#site-search",
          showSubResults: true,
          translations: { placeholder: "Search this site…" }
        });

        const input = search.querySelector("input");
        if (input) input.setAttribute("aria-label", "Search this site");
      };
      document.body.appendChild(pagefindScript);
    }
  }

  const footerMount = document.querySelector("[data-site-footer]");
  if (footerMount) {
    footerMount.outerHTML = siteFooter;
  }

  const year = new Date().getFullYear();
  const el = document.querySelector("[data-year]");
  if (el) el.textContent = year;

  // Basic outbound click tracking hook (no analytics by default).
  // If you add analytics later, attach here.
})();
