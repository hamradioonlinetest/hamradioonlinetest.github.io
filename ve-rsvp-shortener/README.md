# VE RSVP Shortener

This project is a Cloudflare Worker scaffold for generating branded VE RSVP short links.

Future public domain:

```text
https://rsvp.hamradioonlinetest.com
```

## Secrets

Secrets must not be committed to GitHub. Do not place passwords, API keys, Google Apps Script tokens, Cloudflare credentials, or real RSVP URLs in this repository.

`ADMIN_PASS` must be configured later using Cloudflare Worker secrets, for example with `wrangler secret put ADMIN_PASS`.

## KV namespace

The `RSVP_LINKS` KV namespace must be created in Cloudflare and bound later by replacing the placeholder namespace ID in `wrangler.toml`.

## Development

```sh
npm install
npm run dev
```

## Deployment

```sh
npm run deploy
```
