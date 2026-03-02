# AWS deployment runbook (free mode)

This runbook deploys `video2ascii` with Docker Compose, with payment bypass enabled via env var while keeping bearer-token auth required.

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

## Local dev quickstart (macOS/Linux workstation)

Use this section when running locally on your own machine (for example macOS with Docker Desktop). Do not run Linux package-manager steps from the production section below.

```bash
# prereq: Docker Desktop or docker+compose already installed
docker --version
docker compose version
git clone https://github.com/funkatron/video2ascii.git
cd video2ascii
# checkout your deployment branch (example shown)
git checkout feature/public-client-side-app
cd deploy/aws
cp .env.example .env

# macOS-safe secret generation
FREE_SECRET="$(openssl rand -hex 32)"
sed -i.bak "s|^VIDEO2ASCII_FREE_MODE=.*|VIDEO2ASCII_FREE_MODE=true|" .env
sed -i.bak "s|^VIDEO2ASCII_TRANSCRIBE_PROVIDER=.*|VIDEO2ASCII_TRANSCRIBE_PROVIDER=local|" .env
sed -i.bak "s|^VIDEO2ASCII_FREE_ISSUER_SECRET=.*|VIDEO2ASCII_FREE_ISSUER_SECRET=${FREE_SECRET}|" .env
sed -i.bak "s|^VIDEO2ASCII_CORS_ALLOW_ORIGINS=.*|VIDEO2ASCII_CORS_ALLOW_ORIGINS=*|" .env

docker compose up -d --build
docker compose ps
```

Open `http://localhost/public` and set API Base URL to `http://localhost`.

## Production deploy (AWS EC2)

### 1) Launch EC2

- Use Amazon Linux 2023 or Ubuntu 22.04.
- Security group:
  - `22/tcp` from your IP
  - `80/tcp` from the internet

### 2) Install Docker (EC2 host)

Amazon Linux 2023:

```bash
sudo dnf update -y
sudo dnf install -y git docker openssl
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker
```

Install Compose plugin on EC2 Linux host (architecture-aware):

```bash
ARCH="$(uname -m)"
if [ "$ARCH" = "x86_64" ]; then
  COMPOSE_ARCH="x86_64"
elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
  COMPOSE_ARCH="aarch64"
else
  echo "Unsupported CPU architecture: $ARCH" && exit 1
fi

sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL "https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-${COMPOSE_ARCH}" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version
```

### 3) Configure and launch

```bash
git clone https://github.com/funkatron/video2ascii.git
cd video2ascii
# checkout your deployment branch (example shown)
git checkout feature/public-client-side-app
cd deploy/aws
cp .env.example .env

FREE_SECRET="$(openssl rand -hex 32)"
sed -i "s|^VIDEO2ASCII_FREE_MODE=.*|VIDEO2ASCII_FREE_MODE=true|" .env
sed -i "s|^VIDEO2ASCII_TRANSCRIBE_PROVIDER=.*|VIDEO2ASCII_TRANSCRIBE_PROVIDER=local|" .env
sed -i "s|^VIDEO2ASCII_FREE_ISSUER_SECRET=.*|VIDEO2ASCII_FREE_ISSUER_SECRET=${FREE_SECRET}|" .env
sed -i "s|^VIDEO2ASCII_CORS_ALLOW_ORIGINS=.*|VIDEO2ASCII_CORS_ALLOW_ORIGINS=*|" .env

docker compose up -d --build
docker compose ps
```

Open `http://<ec2-public-ip>/public` and set API Base URL to `http://<ec2-public-ip>`.

## Smoke test checklist

1. Open `/public`.
2. Click **Unlock Paid Features**.
3. Verify status says free-mode token was issued.
4. Upload a short video and convert.
5. Run **Auto Subtitle (Paid)** (uses local whisper provider in free mode).
6. Export `.webm` and `.mp4`.

## Notes

- Free mode only bypasses payment, not auth.
- To disable free mode, set `VIDEO2ASCII_FREE_MODE=false` and wire paid billing/transcribe services.
