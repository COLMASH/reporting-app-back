# GCP Quick Reference

## Connect to Server

```bash
gcloud compute ssh malatesta-dev-server --zone=us-central1-a
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

## ngrok Commands

```bash
# Start ngrok tunnel
ngrok http 8000

# Run in background
nohup ngrok http 8000 > /tmp/ngrok.log 2>&1 &

# Get current ngrok URL
curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'

# Check if ngrok is running
ps aux | grep ngrok

# Kill ngrok
pkill ngrok
```

### After Server Restart:
1. SSH into server
2. Start ngrok: `nohup ngrok http 8000 > /tmp/ngrok.log 2>&1 &`
3. Get new URL: `curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'`
4. Update frontend env var with new URL
5. Redeploy frontend on Vercel

---

## Database Commands

```bash
# On GCP server
cd ~/reporting-app-back

# Run migrations
uv run alembic upgrade head

# Check current migration
uv run alembic current

# View migration history
uv run alembic history
```

---

## Server Info

**Instance**: `malatesta-dev-server`
**Zone**: `us-central1-a`
**IP**: `34.9.206.48`
**User**: `proyecto_ai_ilv`
**App Dir**: `/home/proyecto_ai_ilv/reporting-app-back`
**Service**: `reporting-backend`
**Port**: `8000`

---

## Quick Troubleshooting

### Service won't start
```bash
sudo systemctl status reporting-backend
sudo journalctl -u reporting-backend -n 50
```

### Check if app is running
```bash
curl http://localhost:8000/docs
```

### Check environment variables
```bash
cd ~/reporting-app-back
cat .env | grep BACKEND_CORS
```

### Manual restart everything
```bash
sudo systemctl restart reporting-backend
pkill ngrok
nohup ngrok http 8000 > /tmp/ngrok.log 2>&1 &
```

---

## Update Code Manually (if CI/CD fails)

```bash
cd ~/reporting-app-back
git pull origin develop
uv sync --frozen
uv run alembic upgrade head
sudo systemctl restart reporting-backend
```
