(function () {
  const siteHeader = `
  <header class="header">
    <div class="container">
      <div class="nav">
        <a class="brand" href="https://hamradioonlinetest.com/">
          <img src="https://hamradioonlinetest.com/assets/img/wearc-logo.png" alt="WEARC logo">
          <div>
            <div style="font-weight:900; letter-spacing:0.2px;">West Essex Amateur Radio Club</div>
            <div class="tag">Online VE exam sessions and new ham support</div>
          </div>
        </a>
        <nav class="navlinks" aria-label="Site">
          <a href="https://hamradioonlinetest.com/get-licensed/">Get Licensed</a>
          <a href="https://hamradioonlinetest.com/checklist/">Pre-exam Checklist</a>
          <a href="https://hamradioonlinetest.com/community/">Community</a>
          <a href="https://www.wearc.org/" rel="noopener">WEARC Club</a>
          <a class="cta" href="https://hamstudy.org/sessions/WEARC/all" rel="noopener">Find a session</a>
        </nav>
      </div>
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
            <p class="notice">If you plan to take multiple exam elements in one session, email us ahead of time so we can schedule enough time.</p>
          </div>
          <div>
            <div class="kicker">Register</div>
            <p class="notice">Browse dates and register through HamStudy:</p>
            <p><a class="cta" href="https://hamstudy.org/sessions/WEARC/all" rel="noopener">hamstudy.org/sessions/WEARC/all</a></p>
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
