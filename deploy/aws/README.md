# AWS-Only EC2 Deployment (Free Mode)

This runbook deploys `video2ascii` on a single EC2 host using Docker Compose, with payment bypass enabled via env var while keeping bearer-token auth required.

## Operator quickstart

Use this when you want the fastest first bring-up on a fresh Amazon Linux 2023 EC2 host.

```bash
# system deps
sudo dnf update -y
sudo dnf install -y git docker openssl
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker

# Docker Compose plugin
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version

# app checkout + env
git clone https://github.com/funkatron/video2ascii.git
cd video2ascii
git checkout feature/public-client-side-app
cd deploy/aws
cp .env.example .env

FREE_SECRET="$(openssl rand -hex 32)"
sed -i.bak "s|^VIDEO2ASCII_FREE_MODE=.*|VIDEO2ASCII_FREE_MODE=true|" .env
sed -i.bak "s|^VIDEO2ASCII_TRANSCRIBE_PROVIDER=.*|VIDEO2ASCII_TRANSCRIBE_PROVIDER=local|" .env
sed -i.bak "s|^VIDEO2ASCII_FREE_ISSUER_SECRET=.*|VIDEO2ASCII_FREE_ISSUER_SECRET=${FREE_SECRET}|" .env
sed -i.bak "s|^VIDEO2ASCII_CORS_ALLOW_ORIGINS=.*|VIDEO2ASCII_CORS_ALLOW_ORIGINS=*|" .env

# launch
docker compose up -d --build
docker compose ps
```

Quick validation:

1. Open `http://<ec2-public-ip>/public`.
2. Set API Base URL to `http://<ec2-public-ip>`.
3. Click **Unlock Paid Features** and confirm free-mode token unlock.
4. Upload a short clip, convert, auto-subtitle, export `.webm` and `.mp4`.

## What this stack runs

- `web-app` (`video2ascii.web.app`)
  - serves `/` and `/public`
  - issues free-mode access token at `POST /api/billing/free-token` when enabled
  - handles transcription at `POST /api/transcribe` (set `VIDEO2ASCII_TRANSCRIBE_PROVIDER=local`)
- `export-api` (`video2ascii.services.mp4_api`)
  - handles `POST /api/export/mp4` and `POST /api/export/webm`
  - still requires bearer auth
- `reverse-proxy` (nginx)
  - routes `/api/export/*` to export service
  - routes everything else to web app

## 1) Launch EC2

- Use Amazon Linux 2023 or Ubuntu 22.04.
- Security group:
  - `22/tcp` from your IP
  - `80/tcp` from the internet

## 2) Install Docker

Amazon Linux 2023:

```bash
sudo dnf update -y
sudo dnf install -y docker
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker
```

Install Compose plugin:

```bash
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version
```

## 3) Configure app

```bash
git clone https://github.com/funkatron/video2ascii.git
cd video2ascii/deploy/aws
cp .env.example .env
```

Edit `.env` at minimum:

- `VIDEO2ASCII_FREE_MODE=true`
- `VIDEO2ASCII_TRANSCRIBE_PROVIDER=local`
- `VIDEO2ASCII_FREE_ISSUER_SECRET=<long-random-secret>`
- `VIDEO2ASCII_CORS_ALLOW_ORIGINS=<your-origin-or-*>`

## 4) Start services

From `deploy/aws`:

```bash
docker compose up -d --build
docker compose ps
```

Visit `http://<ec2-public-ip>/public`.

## 5) Smoke test

1. Set API Base URL to `http://<ec2-public-ip>`.
2. Click **Unlock Paid Features**.
3. Verify status says free mode token issued.
4. Upload a short video and convert.
5. Run **Auto Subtitle (Paid)** (uses local whisper provider in free mode).
6. Export `.webm` and `.mp4`.

## Notes

- Free mode only bypasses payment, not auth.
- To disable free mode, set `VIDEO2ASCII_FREE_MODE=false` and wire paid billing/transcribe services.
