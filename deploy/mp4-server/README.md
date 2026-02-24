# MP4/WebM Export Service

This service exposes paid export endpoints used by `public.html`.

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

Set `VIDEO2ASCII_EXPORT_TOKEN` to require bearer auth.

## Local run

```bash
uv run uvicorn video2ascii.services.mp4_api:app --reload --port 8080
```

## Docker

```bash
docker build -f deploy/mp4-server/Dockerfile -t video2ascii-mp4-export .
docker run --rm -p 8080:8080 -e VIDEO2ASCII_EXPORT_TOKEN=dev-token video2ascii-mp4-export
```

## Fly.io

1. Copy `fly.toml.example` to `fly.toml` and adjust `app` name.
2. Set secret:
   - `fly secrets set VIDEO2ASCII_EXPORT_TOKEN=...`
3. Deploy:
   - `fly deploy`
