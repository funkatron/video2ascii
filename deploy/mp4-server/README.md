# MP4/WebM Export Service

This service exposes paid export endpoints used by `public.html`.

For AWS-only free-mode deployment on EC2 with compose, see:

- `deploy/aws/README.md`

## Endpoints

- `POST /api/export/webm`
- `POST /api/export/mp4`
- `GET /healthz`

Request body:

```json
{
  "frames": ["...ascii frame..."],
  "fps": 12,
  "width": 120,
  "color": false,
  "crt": false,
  "charset": "classic",
  "font": null
}
```

Set `VIDEO2ASCII_EXPORT_TOKEN` to require bearer auth (recommended for all non-local environments).
In free mode, signed bearer tokens issued by `/api/billing/free-token` are also accepted when:

- `VIDEO2ASCII_FREE_MODE=true`
- `VIDEO2ASCII_FREE_ISSUER_SECRET` is set

If you are running the single-host AWS compose path, this service is started behind nginx and routed at:

- `/api/export/mp4`
- `/api/export/webm`

CORS is enabled for browser clients. Configure allowed origins with:

- `VIDEO2ASCII_CORS_ALLOW_ORIGINS` (default: `*`, comma-separated list supported)

## Local run

```bash
uv run uvicorn video2ascii.services.mp4_api:app --reload --port 8080
```

## Docker

```bash
docker build -f deploy/mp4-server/Dockerfile -t video2ascii-mp4-export .
docker run --rm -p 8080:8080 -e VIDEO2ASCII_EXPORT_TOKEN=dev-token video2ascii-mp4-export
```

Optional limits:

- `VIDEO2ASCII_MAX_REQUEST_BYTES` (default: `20000000`)
- `VIDEO2ASCII_MAX_CHARS_PER_FRAME` (default: `20000`)
- `VIDEO2ASCII_RATE_LIMIT_PER_MINUTE` (default: `20`)

## Fly.io

1. Copy `fly.toml.example` to `fly.toml` and adjust `app` name.
2. Set secret:
   - `fly secrets set VIDEO2ASCII_EXPORT_TOKEN=...`
3. Deploy:
   - `fly deploy`
