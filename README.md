# Jenasaro Website

Public marketing website for Jenasaro.

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
