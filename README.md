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

After this repository is connected to a Netlify project, Netlify automatically
creates a Deploy Preview for each pull request. Preview URLs use Netlify's normal
pattern, for example:

`https://deploy-preview-123--<netlify-site-name>.netlify.app/`

Netlify reads `netlify.toml`, runs `scripts/build-preview-site.sh`, and publishes
`_site/`. The preview build first runs the normal production build, validation,
and Pagefind generation. It then runs `scripts/prepare-preview-site.py` against
the staged copy only. That preview-only step changes same-site asset and
navigation references to root-relative URLs so the preview does not accidentally
load production CSS/JavaScript or send ordinary internal navigation back to the
live site.

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
4. Keep Deploy Previews enabled for pull requests.

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
The workflow is guarded to deploy only from `main`. No new workflow runs or
production changes are needed while reviewing a pull request's Netlify preview.
GitHub Actions caches successful snapshots for transient outages, but only snapshots
less than six hours old may be rendered. A failed first fetch or expired cache
produces a direct HamStudy link, never a claim that no exams exist. Browser-side
expiry also hides past sessions and snapshots older than six hours in open tabs.
Without JavaScript, freshness depends on the scheduled rebuild; HamStudy always
confirms registration availability. Netlify previews fetch on build, not hourly,
so old preview pages will intentionally fall back to the HamStudy link.

Run `python3 scripts/test-hamstudy-sessions.py` for adapter regressions. For an
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
