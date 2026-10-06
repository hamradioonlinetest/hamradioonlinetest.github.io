# WEARC VE Sessions Site

This is a static GitHub Pages site that informs candidates and provides a link to the official HamStudy session list:

- https://hamstudy.org/sessions/WEARC/all

## Site search and deployment

Pagefind 1.5.2 powers the local, browser-side site search. The shared Component UI searchbox is
rendered from `templates/search.html`, enhanced in `assets/js/main.js`, and styled in `assets/css/styles.css`. Searchable
pages mark their primary `<main>` content with `data-pagefind-body`, which keeps
shared navigation, footers, redirects, error pages, and staff/helper pages out of
the index. The component loads its stylesheet, module, and index from the
root-relative `/pagefind/` bundle generated during the production build.

Run `./scripts/build-site.sh` to stage the production site in `_site/`.
The build renders shared HTML and the HamStudy schedule, runs `scripts/validate-site.py`, then generates the Pagefind
index. Validation covers the canonical URLs listed in `sitemap.xml`, including
titles, descriptions, canonical URLs, robots directives, one H1 per page,
Pagefind markers, JSON-LD parsing and shared Organization/WebSite identity,
same-site links, and basic form-label accessibility. It also verifies that the
custom 404 page is `noindex`.

Serve `_site/` over HTTP (for example,
`python3 -m http.server --directory _site 8000`) to test search locally. The
`.github/workflows/validate-site.yml` workflow runs the same build on pull
requests to `main`. The GitHub Pages workflow runs it again on deployment and
uploads the staged site, including `CNAME` and the generated `pagefind/`
directory.

The repository's GitHub Pages **Source** must be set to **GitHub Actions** in
**Settings → Pages → Build and deployment**. Do not select **Deploy from a
branch**: that setting also starts GitHub's legacy `pages build and deployment`
workflow, whose Jekyll artifact omits the generated Pagefind bundle and can
replace the custom deployment. The sole production deployment path is
`.github/workflows/deploy-pages.yml`; generated `_site/` and `pagefind/` output
must not be committed.


## Pull request website previews

Production remains on GitHub Pages at `https://hamradioonlinetest.com/`. Netlify is
used only as an isolated preview host for branches and pull requests.

Netlify previews are **request-only** to conserve credits. Ordinary PRs and commits
use `[skip netlify]`; the checked-in `ignore` command also skips builds by default.
GitHub Actions runs the regular production build and checks without creating or
publishing a preview.

Only after an explicit request for a hosted preview:

1. Remove `[skip netlify]` from that PR's title.
2. Push a branch commit whose message contains `[build preview]`, with no skip token.
3. Netlify builds that commit in `deploy-preview` or `branch-deploy` context only.
   Later ordinary commits are skipped again unless another preview is requested.

Do not use `[build preview]` on production commits. Netlify production-context
builds are always denied: the live website remains on GitHub Pages.
`scripts/netlify-preview.cjs` enforces this policy both before building and in the
build command, because build hooks can bypass an ignore command. An absent or
unreadable request fails closed. The request marker is the explicit authorization;
no repository token or site-wide environment toggle is required.

Authorized preview URLs use Netlify's normal pattern:

`https://deploy-preview-123--<netlify-site-name>.netlify.app/`

For an authorized request, Netlify runs `scripts/build-preview-site.sh` and
publishes `_site/`. That script builds and validates the site, then applies
`scripts/prepare-preview-site.py` to the staged copy only, keeping navigation and
assets on the preview host. For routine work, run `bash scripts/build-site.sh`
locally instead. This performs validation without publishing a hosted preview.

Preview copies are intentionally blocked from search indexing in two ways:
Netlify sends an `X-Robots-Tag: noindex, nofollow, noarchive` header, and the
preview build replaces the staged `robots.txt` with `Disallow: /`. Neither
control is present on the GitHub Pages production site.

One-time Netlify setup:

1. In Netlify, import the GitHub repository
   `hamradioonlinetest/hamradioonlinetest.github.io`.
2. Do not assign `hamradioonlinetest.com` or change DNS; leave the Netlify site
   on its `.netlify.app` hostname.
3. Let Netlify use the repository's `netlify.toml` build settings.
4. Keep the repository build and ignore commands; previews remain opt-in even if
   Netlify has Deploy Previews enabled.

No Netlify token or secret is required in this repository when Netlify's GitHub
integration is used.

## Server-rendered navigation and upcoming online sessions

Shared header, search markup, and footer live in `templates/`. `scripts/render-site.py`
expands the source HTML mounts in `_site/` before validation and Pagefind indexing.
JavaScript only enhances search, the copyright year, and expired-session handling.
Always preview the built `_site/` directory rather than serving the source root.

The homepage's next six online session links are generated from the public
`https://hamstudy.org/sessions/WEARC/remote` listing, which excludes full sessions
by default. HamStudy/ExamTools remains the only schedule editors maintain.
No private exam/candidate data, account credentials, seat counts, or invented dates
are used. The adapter reads HamStudy's epoch timestamps and formats Eastern time
with daylight saving handling. It validates team identity, URLs, and markup before
replacing the cached snapshot. HamStudy does not provide a verified supported API
for this integration; changes to its public HTML may require updating the adapter.

Every build fetches the listing. Once approved and merged to `main`, the Pages
workflow also rebuilds at minute 17 of each hour (GitHub may delay scheduled runs).
The workflow is guarded to deploy only from `main`. Routine PR validation does not
deploy to production or create a hosted preview.
Transient network errors, HTTP 429, and HTTP 5xx responses are retried up to three
times before falling back to the last successful snapshot. Invalid markup and other
HTTP errors are not retried. GitHub Actions caches successful snapshots for outages.
Snapshots remain usable for less than 48 hours, with a visible reminder to confirm
dates on HamStudy after six hours. This grace period accommodates delayed scheduled
builds without presenting old availability as a live feed. The original check time
is preserved when using the cache. A failed first fetch or expired cache produces a
direct HamStudy link, never a claim that no exams exist. Browser-side expiry hides
started sessions immediately, adds the six-hour notice in open tabs, and hides all
dates once their snapshot reaches 48 hours.
Without JavaScript, freshness depends on the scheduled rebuild; HamStudy always
confirms registration availability. Netlify previews fetch on build, not hourly,
so old preview pages will intentionally fall back to the HamStudy link.

Run `python3 scripts/test-hamstudy-sessions.py` and
`node scripts/test-session-display.cjs` for adapter and browser regressions. For an
offline build, set `HAMSTUDY_HTML_FIXTURE` to a captured public listing. Cached files
stay in ignored `.cache/`; they are never committed or copied to the public site.

Operational `/sessions/`, `/counts/`, and `/vescript/` pages use `noindex` and are
crawlable so bots can see that instruction. These pages remain public; `noindex`
is not an access control. Preview deployments still retain their separate
Netlify noindex header and robots block.

## Breadcrumbs and sitemap modification dates

The public URLs in `sitemap.xml` define which pages receive build-time metadata.
Every public page other than the homepage gets visible Home → page breadcrumbs
and matching `BreadcrumbList` JSON-LD linked from its `WebPage` entity.

`scripts/site_metadata.py` generates sitemap `lastmod` dates. A full Git checkout
provides the initial known source-change date; if history is incomplete, unknown
dates are omitted rather than guessed. Later builds compare substantive visible
content, links, media, descriptions, and structured data against the cached prior
build. Changes to the displayed HamStudy sessions count as content changes;
fetch/check timestamps, copyright years, and cosmetic markup do not. Unchanged
hourly builds preserve the previous date. GitHub Actions restores and saves
`.cache/sitemap-state.json` alongside the public schedule snapshot. The state is
not committed or published. Cache loss resets tracking to the known Git date;
it cannot reconstruct past dynamic schedule changes.

Run `python3 scripts/test-site-metadata.py` to check date stability, real schedule
changes, missing history, and agreement between visible and schema breadcrumbs.
These checks also run during every site build.

## Shared link styling

Text links share a burgundy color, a visible underline, and a darker hover/focus
treatment across paragraphs, resource lists, callouts, breadcrumbs, footer, and
redirect fallbacks. Homepage resources retain their generous row spacing but use
the same text-link appearance. Navigation, the logo, and primary/secondary
buttons have explicit role-based exceptions shared by all pages. Keep future
changes in this central stylesheet rather than adding page-specific link rules.
