# Website review preferences

- Netlify previews are opt-in. Do not create, trigger, or retry a hosted preview unless the user explicitly requests it.
- Use `[skip netlify]` in ordinary PR titles and commit messages so unmerged branches cannot trigger previews either.
- After an explicit preview request, remove the skip token from the PR title and put `[build preview]` in the latest branch commit. Never use this marker for a routine change or production commit.
- Validate ordinary changes with `bash scripts/build-site.sh`; GitHub Actions also validates without deploying a preview.
- Keep one shared text-link treatment across content, lists, callouts, breadcrumbs, and footer. Navigation and primary/secondary buttons have distinct, consistent roles.

## Pull request Codex reviews

- Every PR must be checked for Codex automated review feedback and review threads, including comments that arrive after the initial validation run. Passing GitHub Actions alone is not enough to report the PR complete.
- For each substantive Codex finding, assess whether it is correct and applicable. Implement accepted changes and add/adjust regression tests when appropriate. If rejecting a finding, reply in its GitHub review thread with a detailed, technically grounded reason.
- Reply to addressed review threads with the disposition and commit references; resolve threads only after the issue is addressed. Recheck new comments and GitHub Actions after changes.
- Keep PRs open for human merge approval; never merge solely because validation and Codex review passed.
