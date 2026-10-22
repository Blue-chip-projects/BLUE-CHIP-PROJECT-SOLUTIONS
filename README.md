# Jenasaro Website

Public marketing website for Jenasaro.

## Search discovery checks

Run `python scripts/check_search.py` and `python -m unittest discover -s scripts -p 'test_*.py'` before publishing. After deployment, run `python scripts/check_search.py --live` to verify the sitemap, all listed pages, canonical URLs, metadata, crawler rules, IndexNow ownership key and real HTTP 404 responses.

Keep the top-level `404.html`: without it Cloudflare Pages treats this static site as a single-page app and serves the homepage for nonexistent URLs. Keep the existing Google verification tag and IndexNow key file.

The search workflow validates pull requests. On production pushes it waits for the **Cloudflare Pages** check to succeed for the exact commit, verifies the live site, and only then notifies IndexNow. A successful notification confirms receipt, not search indexing or AI inclusion. Google indexing and sitemap processing must still be checked in Search Console; Bing Webmaster verification and Cloudflare account rules are managed outside this repository.

## Structure

- `index.html` — main marketing site
- `interest.html` — interest / demo registration form
- `privacy.html` — launch privacy-notice draft
- `styles.css` — Jenasaro brand and responsive layout
- `site.js` — navigation and form submission
- `functions/api/interest.js` — Cloudflare Pages Function for lead capture
- `jenasaro-*.svg` — current Jenasaro brand assets

## Cloudflare Pages deployment

Use this repository as the Cloudflare Pages source.

- Framework preset: **None**
- Build command: leave blank
- Build output directory: **/**
- Production branch: **main**

Attach the public domain to the Pages project, for example `jenasaro.com` and `www.jenasaro.com`.

## Interest form storage

The Pages Function stores each submitted lead in a Cloudflare KV namespace.

1. Create a Workers KV namespace for website leads.
2. In the Pages project, add a KV namespace binding named exactly:
   `JENASARO_LEADS`
3. Bind it to the namespace in both Preview and Production as required.
4. Redeploy the Pages project.

The form endpoint is `/api/interest`. It validates required fields, includes a honeypot field for simple bot filtering, and stores a timestamped JSON lead record.

## Before public launch

Replace the draft privacy notice with the final legal entity name, business address and privacy contact details. Confirm the domain and platform-login URL before launch.
