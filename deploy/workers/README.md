# Cloudflare Workers for Paid Tier

Two workers are provided:

- `stripe-worker.js`: creates Stripe Checkout sessions and mints signed paid tokens.
- `whisper-worker.js`: validates paid token and proxies transcription to OpenAI.

For AWS-only deployments that do not use Cloudflare Workers, see:

- `deploy/aws/README.md`

## 1) Stripe Worker

Copy:

- `wrangler.stripe.toml.example` -> `wrangler.toml`

Set secrets:

```bash
wrangler secret put STRIPE_SECRET_KEY
wrangler secret put TOKEN_SIGNING_SECRET
wrangler secret put ALLOWED_RETURN_ORIGINS
wrangler secret put CORS_ALLOW_ORIGINS
wrangler secret put VIDEO2ASCII_FREE_MODE
wrangler secret put VIDEO2ASCII_FREE_TOKEN_TTL_SECONDS
```

Set `PRICE_ID` in `wrangler.toml`, then deploy:

```bash
wrangler deploy
```

## 2) Whisper Worker

Copy:

- `wrangler.whisper.toml.example` -> `wrangler.toml`

Set secrets:

```bash
wrangler secret put OPENAI_API_KEY
wrangler secret put TOKEN_SIGNING_SECRET
wrangler secret put MAX_UPLOAD_BYTES
wrangler secret put CORS_ALLOW_ORIGINS
wrangler secret put VIDEO2ASCII_TRANSCRIBE_PROVIDER
wrangler secret put VIDEO2ASCII_LOCAL_TRANSCRIBE_URL
wrangler secret put VIDEO2ASCII_LOCAL_TRANSCRIBE_SECRET
```

Notes:

- `CORS_ALLOW_ORIGINS` is a comma-separated list of allowed browser origins.
- If omitted, workers default to `*` for development convenience.
- Workers now respond to `OPTIONS` preflight for browser `POST` calls with `Authorization`/JSON headers.
- Stripe worker exposes `POST /api/billing/free-token` when `VIDEO2ASCII_FREE_MODE=true`.
- Whisper worker supports `VIDEO2ASCII_TRANSCRIBE_PROVIDER=local` via `VIDEO2ASCII_LOCAL_TRANSCRIBE_URL`.

Deploy:

```bash
wrangler deploy
```

## Public app wiring

Set `API Base URL` in `public.html` to your worker/API domain.
The app expects:

- `POST /api/billing/checkout` -> `{ checkout_url }`
- `POST /api/billing/exchange` -> `{ token }`
- `POST /api/transcribe` -> `{ srt }`
- `POST /api/export/mp4` -> binary mp4 response
- `POST /api/export/webm` -> binary webm response
