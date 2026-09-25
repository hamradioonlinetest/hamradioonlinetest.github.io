# WEARC VE Sessions Site

This is a static GitHub Pages site that informs candidates and provides a link to the official HamStudy session list:

- https://hamstudy.org/sessions/WEARC/all

## Site search and deployment

Pagefind 1.5.2 powers the local, browser-side site search. The shared Component UI searchbox is
created in `assets/js/main.js` and styled in `assets/css/styles.css`. Searchable
pages mark their primary `<main>` content with `data-pagefind-body`, which keeps
shared navigation, footers, redirects, error pages, and staff/helper pages out of
the index. The component loads its stylesheet, module, and index from the
root-relative `/pagefind/` bundle generated during the production build.

Run `./scripts/build-site.sh` to stage the production site in `_site/`.
The build first runs `scripts/validate-site.py`, then generates the Pagefind
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
