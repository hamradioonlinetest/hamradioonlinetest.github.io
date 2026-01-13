# WEARC VE Sessions Funnel Site (GitHub Pages)

This is a static GitHub Pages site that funnels exam candidates to the official HamStudy session list:

- https://hamstudy.org/sessions/WEARC/all

## Quick start

1. Create a new GitHub repo (public is easiest for Pages).
2. Copy the contents of this folder into the repo root.
3. In GitHub: Settings -> Pages -> Build and deployment -> Source: Deploy from a branch -> Branch: `main` / folder: `/ (root)`.
4. Update `site.config.json` and the `base_url` placeholder to your real Pages URL, then update these values in the HTML files:
   - `https://YOUR-GITHUB-USERNAME.github.io/YOUR-REPO/`

Why: canonical URLs and the sitemap need the real base URL for best SEO.

## Files included

- `index.html` main landing page
- `get-licensed/` sign-up guide
- `new-ham-starter-kit/` community value and station building guide
- `community/` community and mentoring page
- `robots.txt` and `sitemap.xml` for SEO
- Open Graph image: `assets/img/og.png`

## Edit content

All site copy is plain HTML inside each page. Styles are in `assets/css/styles.css`.
