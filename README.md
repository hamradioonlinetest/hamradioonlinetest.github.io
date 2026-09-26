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
