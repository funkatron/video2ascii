# Cloudflare Workers for Paid Tier

Two workers are provided:

- `stripe-worker.js`: creates Stripe Checkout sessions and mints signed paid tokens.
- `whisper-worker.js`: validates paid token and proxies transcription to OpenAI.

## 1) Stripe Worker

Copy:

- `wrangler.stripe.toml.example` -> `wrangler.toml`

Set secrets:

```bash
wrangler secret put STRIPE_SECRET_KEY
wrangler secret put TOKEN_SIGNING_SECRET
wrangler secret put ALLOWED_RETURN_ORIGINS
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
```

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
