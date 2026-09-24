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

Run `./scripts/build-site.sh` to stage the production site in `_site/` and build
its Pagefind index. Serve `_site/` over HTTP (for example,
`python3 -m http.server --directory _site 8000`) to test search locally. The
GitHub Pages workflow runs the same command on every deployment and uploads the
staged site, including `CNAME` and the generated `pagefind/` directory.
