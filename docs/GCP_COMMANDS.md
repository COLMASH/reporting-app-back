# GCP Quick Reference

## Server Info

| | DEV | PROD |
|---|-----|------|
| **Instance** | `malatesta-dev-server` | `malatesta-prod-server` |
| **Zone** | `us-central1-a` | `us-central1-a` |
| **User** | `proyecto_ai_ilv` | `proyecto_ai_ilv` |
| **Branch** | `develop` | `master` |
| **App Dir** | `/home/proyecto_ai_ilv/reporting-app-back` | `/home/proyecto_ai_ilv/reporting-app-back` |
| **Port** | `8000` | `8000` |
| **Services** | `reporting-backend`, `cloudflared` | `reporting-backend`, `cloudflared` |

---

## Connect to Servers

```bash
# DEV server
gcloud compute ssh proyecto_ai_ilv@malatesta-dev-server --zone=us-central1-a

# PROD server
gcloud compute ssh proyecto_ai_ilv@malatesta-prod-server --zone=us-central1-a
```

---

## Service Commands

```bash
# Check service status
sudo systemctl status reporting-backend

# View live logs
sudo journalctl -u reporting-backend -f

# Restart service
sudo systemctl restart reporting-backend

# Stop service
sudo systemctl stop reporting-backend

# Start service
sudo systemctl start reporting-backend
```

---

## View Logs

```bash
# Last 50 lines
sudo journalctl -u reporting-backend -n 50

# Last hour
sudo journalctl -u reporting-backend --since "1 hour ago"

# Today's logs
sudo journalctl -u reporting-backend --since today

# Search for errors
sudo journalctl -u reporting-backend | grep -i error
```

---

## Cloudflare Tunnel

> **IMPORTANT:** Cloudflare Tunnel URLs change when the `cloudflared` service restarts!
> After a server restart, you MUST update the Vercel environment variables with the new URL.

### Tunnel Commands

```bash
# Check tunnel status
sudo systemctl status cloudflared

# View tunnel logs (shows current URL)
sudo journalctl -u cloudflared -n 30

# Restart tunnel (will generate NEW URL!)
sudo systemctl restart cloudflared

# Get current tunnel URL
sudo journalctl -u cloudflared | grep "trycloudflare.com" | tail -1
```

### After Server/Tunnel Restart

1. SSH into the restarted server
2. Get new tunnel URL:
   ```bash
   sudo journalctl -u cloudflared | grep "trycloudflare.com" | tail -1
   ```
3. Update Vercel environment variable:
   - DEV server → Update `Preview` environment `NEXT_PUBLIC_API_URL`
   - PROD server → Update `Production` environment `NEXT_PUBLIC_API_URL`
4. Redeploy frontend on Vercel (or wait for next deploy)

---

## CI/CD Deployment

Deployments are automatic via GitHub Actions:

| Branch | Server | Workflow |
|--------|--------|----------|
| `develop` | DEV | `.github/workflows/deploy-develop.yml` |
| `master` | PROD | `.github/workflows/deploy-production.yml` |

### Manual Deployment (if CI/CD fails)

```bash
# On DEV server
cd ~/reporting-app-back
git fetch origin
git checkout develop
git pull origin develop
uv sync --frozen
uv run alembic upgrade head
sudo systemctl restart reporting-backend

# On PROD server
cd ~/reporting-app-back
git fetch origin
git checkout master
git pull origin master
uv sync --frozen
uv run alembic upgrade head
sudo systemctl restart reporting-backend
```

---

## Database Commands

```bash
cd ~/reporting-app-back

# Run migrations
uv run alembic upgrade head

# Check current migration
uv run alembic current

# View migration history
uv run alembic history
```

---

## Quick Troubleshooting

### Service won't start

```bash
sudo systemctl status reporting-backend
sudo journalctl -u reporting-backend -n 50
```

### Check if app is running

```bash
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

### Check environment variables

```bash
cd ~/reporting-app-back
cat .env | head -20
```

### Restart everything

```bash
sudo systemctl restart reporting-backend
sudo systemctl restart cloudflared
# Then get new tunnel URL and update Vercel!
```

---

## GitHub Secrets Reference

### DEV Server Secrets

| Secret | Description |
|--------|-------------|
| `GCP_SSH_PRIVATE_KEY` | SSH private key |
| `GCP_HOST` | DEV server IP |
| `GCP_USER` | `proyecto_ai_ilv` |
| `GCP_APP_DIR` | `/home/proyecto_ai_ilv/reporting-app-back` |

### PROD Server Secrets

| Secret | Description |
|--------|-------------|
| `GCP_SSH_PRIVATE_KEY_PROD` | SSH private key (can be same as DEV) |
| `GCP_HOST_PROD` | PROD server IP |
| `GCP_USER_PROD` | `proyecto_ai_ilv` |
| `GCP_APP_DIR_PROD` | `/home/proyecto_ai_ilv/reporting-app-back` |
