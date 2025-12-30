# DigitalOcean Deployment Guide

Deploy your UFE Research Writer agent to DigitalOcean using App Platform or Droplets.

## Prerequisites

1. **DigitalOcean Account**
   - Sign up at [digitalocean.com](https://www.digitalocean.com/)
   - Add a payment method

2. **doctl CLI** (DigitalOcean command-line tool)
   ```bash
   # macOS
   brew install doctl

   # Linux
   snap install doctl

   # Or download from: https://docs.digitalocean.com/reference/doctl/how-to/install/
   ```

3. **API Keys**
   - Google API Key (Gemini)
   - Tavily API Key

---

## Option 1: App Platform (Recommended) ⭐

**Best for:** Quick deployment, auto-scaling, managed infrastructure

### Pricing
- **Basic**: $5-12/month (512MB-1GB RAM)
- **Professional**: $12-24/month (1-2GB RAM) - Recommended
- Auto-scaling available

### Quick Deployment

#### Method A: One-Click Deploy (Easiest)

1. **Push your code to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for DigitalOcean deployment"
   git push origin main
   ```

2. **Edit `.do/app.yaml`**
   - Update `github.repo` with your GitHub username/repo

3. **Deploy using doctl**
   ```bash
   # Authenticate
   doctl auth init

   # Run deployment script
   ./deploy-digitalocean.sh
   ```

4. **Set secrets in DigitalOcean Dashboard**
   - Go to your app settings
   - Add environment variables:
     - `GOOGLE_API_KEY`: Your Gemini API key
     - `TAVILY_API_KEY`: Your Tavily API key

5. **Wait for deployment** (~5 minutes)
   - DigitalOcean will build and deploy automatically

#### Method B: Manual via Dashboard

1. **Go to** [cloud.digitalocean.com/apps](https://cloud.digitalocean.com/apps)

2. **Click "Create App"**

3. **Connect GitHub Repository**
   - Authorize DigitalOcean to access your repo
   - Select the `finance-research-agent` repository
   - Choose `main` branch

4. **Configure Build**
   - Dockerfile path: `Dockerfile.adk-web`
   - HTTP Port: `8080`
   - HTTP Routes: `/`

5. **Set Environment Variables**
   ```
   GOOGLE_API_KEY=your-google-api-key (encrypted)
   TAVILY_API_KEY=your-tavily-api-key (encrypted)
   LANGUAGE=mn
   PORT=8080
   ```

6. **Choose Plan**
   - Recommended: Professional XS (1GB RAM, 1 vCPU) - $12/month
   - Basic works but may be slower

7. **Add Health Check**
   - Path: `/healthz`
   - Port: `8080`

8. **Deploy**
   - Click "Create Resources"
   - Wait 5-10 minutes

9. **Get Your URL**
   - DigitalOcean provides: `https://your-app-name.ondigitalocean.app`

### Auto-Deployment

App Platform automatically redeploys when you push to GitHub:

```bash
git add .
git commit -m "Update agent"
git push origin main
# DigitalOcean automatically builds and deploys!
```

---

## Option 2: Droplet Deployment

**Best for:** Full control, custom configuration, multiple services

### Pricing
- **Basic Droplet**: $6/month (1GB RAM, 1 vCPU)
- **General Purpose**: $18/month (2GB RAM, 2 vCPU) - Recommended

### Setup Steps

#### 1. Create Droplet

```bash
# Create Ubuntu droplet
doctl compute droplet create ufe-research-writer \
  --image ubuntu-22-04-x64 \
  --size s-2vcpu-2gb \
  --region nyc1 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header)

# Get droplet IP
doctl compute droplet list
```

Or via dashboard:
1. Go to [cloud.digitalocean.com/droplets](https://cloud.digitalocean.com/droplets)
2. Click "Create Droplet"
3. Choose Ubuntu 22.04
4. Select size: Basic 2GB ($18/mo)
5. Add SSH key
6. Create

#### 2. SSH into Droplet

```bash
# Get droplet IP from dashboard or CLI
ssh root@YOUR_DROPLET_IP
```

#### 3. Install Dependencies

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Git
apt install git -y
```

#### 4. Clone Repository

```bash
cd /opt
git clone https://github.com/YOUR_USERNAME/finance-research-agent.git
cd finance-research-agent
```

#### 5. Configure Environment

```bash
# Create .env file
cp .env.example .env
nano .env
# Add your API keys, then save (Ctrl+X, Y, Enter)
```

#### 6. Build and Run

```bash
# Build Docker image
docker build -t ufe-research-writer -f Dockerfile.adk-web .

# Run container
docker run -d \
  --name ufe-research-writer \
  --restart unless-stopped \
  -p 80:8080 \
  --env-file .env \
  ufe-research-writer

# Check logs
docker logs -f ufe-research-writer
```

#### 7. Configure Firewall

```bash
# Allow HTTP/HTTPS
ufw allow 80
ufw allow 443
ufw allow OpenSSH
ufw enable
```

#### 8. Set Up Domain (Optional)

1. **Point domain to droplet IP**
   - Add A record: `@` → `YOUR_DROPLET_IP`
   - Add A record: `www` → `YOUR_DROPLET_IP`

2. **Install Nginx + Let's Encrypt**
   ```bash
   apt install nginx certbot python3-certbot-nginx -y

   # Create Nginx config
   nano /etc/nginx/sites-available/ufe-research-writer
   ```

   Add:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com www.your-domain.com;

       location / {
           proxy_pass http://localhost:8080;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
           proxy_read_timeout 900s;
       }
   }
   ```

   ```bash
   # Enable site
   ln -s /etc/nginx/sites-available/ufe-research-writer /etc/nginx/sites-enabled/
   nginx -t
   systemctl reload nginx

   # Get SSL certificate
   certbot --nginx -d your-domain.com -d www.your-domain.com
   ```

#### 9. Auto-Updates (Optional)

```bash
# Create update script
cat > /opt/update-app.sh << 'EOF'
#!/bin/bash
cd /opt/finance-research-agent
git pull
docker build -t ufe-research-writer -f Dockerfile.adk-web .
docker stop ufe-research-writer
docker rm ufe-research-writer
docker run -d \
  --name ufe-research-writer \
  --restart unless-stopped \
  -p 80:8080 \
  --env-file .env \
  ufe-research-writer
EOF

chmod +x /opt/update-app.sh
```

---

## Comparison: App Platform vs Droplet

| Feature | App Platform | Droplet |
|---------|-------------|---------|
| **Setup Time** | 5 minutes | 30-60 minutes |
| **Maintenance** | Zero | Manual updates |
| **Auto-Scaling** | Yes | No (manual) |
| **SSL/HTTPS** | Automatic | Manual (Certbot) |
| **Price (2GB)** | $12/month | $18/month |
| **GitHub Auto-Deploy** | Yes | Manual setup |
| **Best For** | Quick start, ease of use | Full control, learning |

---

## Testing Your Deployment

### Health Check
```bash
curl https://your-app.ondigitalocean.app/healthz
# or
curl http://YOUR_DROPLET_IP/healthz
```

### Create Session
```bash
curl -X POST https://your-app.ondigitalocean.app/sessions \
  -H 'Content-Type: application/json' \
  -d '{"user_id": "test-user"}'
```

### Send Message
```bash
curl -X POST https://your-app.ondigitalocean.app/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "test-user",
    "session_id": "session-1",
    "message": "Сайн байна уу?"
  }'
```

---

## Monitoring

### App Platform
- Built-in metrics: CPU, Memory, HTTP requests
- View in: Apps → Your App → Insights
- Real-time logs in dashboard

### Droplet
```bash
# View logs
docker logs -f ufe-research-writer

# Resource usage
docker stats

# System resources
htop
```

---

## Troubleshooting

### App Platform Issues

**Build fails:**
- Check build logs in dashboard
- Verify Dockerfile.adk-web exists
- Check requirements.txt is complete

**503 errors:**
- Check environment variables are set
- Verify API keys are correct
- Check resource limits (upgrade plan if needed)

**Deployment stuck:**
- Cancel and redeploy
- Check GitHub connection

### Droplet Issues

**Container won't start:**
```bash
docker logs ufe-research-writer
# Check for errors, verify .env file
```

**Out of memory:**
```bash
# Upgrade droplet or add swap
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
```

**Can't access externally:**
```bash
# Check firewall
ufw status
# Check if container is running
docker ps
```

---

## Cost Optimization

1. **Use App Platform Basic** for development ($5-6/month)
2. **Upgrade to Professional** for production ($12/month)
3. **Scale down during off-hours** (manual or automated)
4. **Monitor usage** to avoid over-provisioning

---

## Security Best Practices

1. **Use encrypted environment variables** for secrets
2. **Enable HTTPS** (automatic on App Platform)
3. **Restrict firewall** to necessary ports only
4. **Regular updates** (automatic on App Platform)
5. **Monitor logs** for suspicious activity

---

## Next Steps

1. **Deploy using App Platform** (recommended first)
2. **Test all endpoints** with sample requests
3. **Set up custom domain** (optional)
4. **Configure monitoring/alerts**
5. **Enable auto-deployment** from GitHub

For questions or issues, refer to:
- [DigitalOcean App Platform Docs](https://docs.digitalocean.com/products/app-platform/)
- [DigitalOcean Droplets Docs](https://docs.digitalocean.com/products/droplets/)
