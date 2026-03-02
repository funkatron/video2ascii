# Public Deployment Guide

This guide deploys `video2ascii/web/static/public.html` with optional paid services.

## AWS-only quick path

For a fully AWS-hosted first run (EC2 + Docker Compose + free mode), use:

- `deploy/aws/README.md` (canonical runbook)

This path keeps bearer auth enabled and bypasses payment only when
`VIDEO2ASCII_FREE_MODE=true`.

It now includes:

- local workstation flow (macOS/Linux with Docker Desktop or docker+compose)
- production EC2 flow
- architecture-aware Compose plugin install (`x86_64` vs `aarch64`)

## Phase 1 (Free)

1. Host static assets (`video2ascii/web/static/`) on Cloudflare Pages.
2. Use `public.html` as the entry page.
3. Users get client-side conversion, playback, `.sh`, and local `.webm` export.

## Phase 1.5 (Backend WebM parity)

Already implemented in OSS backend:

- CLI: `--export-webm`
- Web app endpoint: `GET /api/jobs/{id}/export/webm`

## Phase 2 (Paid subtitles)

Deploy workers in `deploy/workers`:

- `stripe-worker.js` for checkout/token
- `whisper-worker.js` for paid transcription proxy

Set CORS origins for browser calls:

```bash
wrangler secret put CORS_ALLOW_ORIGINS
```

Use a comma-separated allowlist (for example your Pages URL and local dev origin).

Configure `API Base URL` in `public.html` UI to your deployed domain.

## Phase 3 (Paid MP4 export)

Deploy `deploy/mp4-server/Dockerfile` to Fly.io.

Set secret:

```bash
fly secrets set VIDEO2ASCII_EXPORT_TOKEN=replace_me
```

Recommended hardening envs:

```bash
fly secrets set VIDEO2ASCII_MAX_REQUEST_BYTES=20000000
fly secrets set VIDEO2ASCII_MAX_CHARS_PER_FRAME=20000
fly secrets set VIDEO2ASCII_RATE_LIMIT_PER_MINUTE=20
fly secrets set VIDEO2ASCII_CORS_ALLOW_ORIGINS=https://your-pages-domain
```

Expose endpoint(s):

- `POST /api/export/mp4`
- `POST /api/export/webm` (optional backend path used by public app)
