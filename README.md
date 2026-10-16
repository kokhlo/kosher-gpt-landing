# kosherno.app

Static site for KosherGPT, served by GitHub Pages from the root of `main` (custom domain in `CNAME`). A push to `main` publishes it.

The design follows the iOS app: its palette from `KosherGPT/Design/KosherTheme.swift`, the Rubik font and the arch icon.

## Pages

| Page | English (default) | Russian | Hebrew |
|---|---|---|---|
| Home | `/` | `/ru/` | `/he/` |
| For kashrut organizations, with the contact form | `/partners/` | `/ru/partners/` | `/he/partners/` |

## Edit

- Texts: `content/en.json`, `content/ru.json`, `content/he.json`. Keep the three files in the same shape.
- Styles and behaviour: `assets/site.css`, `assets/site.js`.
- Page structure, SEO tags and forms: `tools/build.py`.
- Icons and link previews: `python3 tools/images.py`. It reads the app icon and the Rubik font from the sibling `kosher-gpt-ios` repo. Re-run it when a heading or the icon changes.

## Local preview

```bash
# terminal 1: the form Worker, prints each mail instead of sending it
cd ../kosher-forms-worker && cp -n .dev.vars.example .dev.vars && npm install && npm run dev
# terminal 2: the site
python3 tools/build.py --dev && python3 tools/dev_server.py
```

Open http://127.0.0.1:8787/ and http://127.0.0.1:8787/ru/partners/. The preview lives in `.preview/` (not committed) and uses Cloudflare's always-passing Turnstile test key.

## Forms

Both forms (the beta invite on the home page and the kashrut organizations form) post JSON to the `kosher-forms` Cloudflare Worker in `../kosher-forms-worker`. It checks Cloudflare Turnstile and mails the team through Resend, the same setup as the SoftSys sites. The site has no server of its own.

`site.config.json` holds the Worker address (`form_endpoint`, `https://…/contact`) and the Turnstile site key (`turnstile_sitekey`). Without both the production build stops on purpose, so a form that goes nowhere cannot ship. Setting up the Worker, Resend and Turnstile: `../kosher-forms-worker/README.md`.

## Publish

`python3 tools/build.py`, commit the generated pages (`index.html`, `ru/`, `he/`, `partners/`, `sitemap.xml`, `robots.txt`, `404.html`, `site.webmanifest`) together with `assets/` (styles, script, fonts, icons, OG images), and push to `main`. GitHub Pages serves the repository root, so everything committed is public; nothing here is secret.
