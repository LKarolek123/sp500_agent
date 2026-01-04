# Docker + systemd Deployment Guide

## 1. Build Docker image

```bash
cd sp500_agent
docker build -t sp500-bot:latest .
```

## 2. Run locally (test)

```bash
docker run -e ALPACA_API_KEY="your_key" \
           -e ALPACA_SECRET_KEY="your_secret" \
           -e ALPACA_BASE_URL="https://paper-api.alpaca.markets" \
           sp500-bot:latest
```

## 3. Deploy na Oracle Free Tier / Hetzner

### SSH do serwera

```bash
ssh root@your_server_ip
```

### Clone repo

```bash
git clone https://github.com/yourusername/sp500_agent.git
cd sp500_agent
```

### Build image

```bash
docker build -t sp500-bot:latest .
```

### Create .env file (gitignored)

```bash
cat > .env << EOF
ALPACA_API_KEY=your_api_key_id
ALPACA_SECRET_KEY=your_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets
EOF

chmod 600 .env
```

### Install systemd service

```bash
# Copy service file
sudo cp sp500_bot.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service (auto-start on reboot)
sudo systemctl enable sp500_bot

# Start service
sudo systemctl start sp500_bot

# Check status
sudo systemctl status sp500_bot

# View logs (live)
sudo journalctl -u sp500_bot -f
```

### Manage service

```bash
# Stop bot
sudo systemctl stop sp500_bot

# Restart
sudo systemctl restart sp500_bot

# View last 50 lines
sudo systemctl log -n 50

# Full journalctl
journalctl -u sp500_bot --since today
```

## 4. Docker Compose (optional, for local multi-container)

Create `docker-compose.yml`:

```yaml
version: "3.8"
services:
  bot:
    build: .
    env_file: .env
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
```

Run:

```bash
docker-compose up -d
```

## 5. Oracle Free Tier Setup (if using that)

1. Create Ubuntu 22.04 instance (free tier eligible)
2. Allow traffic on ports you need (default none for bot)
3. Install Docker:
   ```bash
   curl -sSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   ```
4. Follow deployment steps above

## 6. Monitoring

### Real-time logs

```bash
sudo journalctl -u sp500_bot -f
```

### Uptime checker (cron job on server)

```bash
# Add to crontab:
*/5 * * * * systemctl is-active --quiet sp500_bot || systemctl restart sp500_bot
```

### Telegram alerts (optional)

Modify [src/live/live_trader_alpaca.py](../src/live/live_trader_alpaca.py) to send Telegram messages on trade execution.

## 7. Security Notes

⚠️ **Important:**

- `.env` file is gitignored (safe)
- Use `chmod 600 .env` (readable only by owner)
- Docker container runs in isolation
- Consider firewall rules on VPS
- Regularly update system: `sudo apt update && sudo apt upgrade`

## 8. Troubleshooting

**Service won't start:**

```bash
sudo systemctl status sp500_bot -l
journalctl -u sp500_bot -n 20
```

**Docker image issues:**

```bash
docker build --no-cache -t sp500-bot:latest .
```

**Port conflicts** (if adding web dashboard later):

```bash
sudo netstat -tulpn | grep LISTEN
```

---

**Author**: Karol  
**License**: MIT
