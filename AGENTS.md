# Website review preferences

- Netlify previews are opt-in. Do not create, trigger, or retry a hosted preview unless the user explicitly requests it.
- Use `[skip netlify]` in ordinary PR titles and commit messages so unmerged branches cannot trigger previews either.
- After an explicit preview request, remove the skip token from the PR title and put `[build preview]` in the latest branch commit. Never use this marker for a routine change or production commit.
- Validate ordinary changes with `bash scripts/build-site.sh`; GitHub Actions also validates without deploying a preview.
- Keep one shared text-link treatment across content, lists, callouts, breadcrumbs, and footer. Navigation and primary/secondary buttons have distinct, consistent roles.
