# DigitalOcean Spaces Setup for File Downloads

Your app now automatically uploads generated `.docx` files to DigitalOcean Spaces (S3-compatible storage) so users can download them.

## Quick Setup

### 1. Create a Space

```bash
# Via CLI
doctl spaces create ufe-reports --region nyc3

# Or via dashboard: https://cloud.digitalocean.com/spaces
# Click "Create a Space" → Name: ufe-reports → Region: NYC3
```

**Cost:** $5/month (250 GB storage, 1 TB transfer)

### 2. Create API Keys

```bash
# Via dashboard: https://cloud.digitalocean.com/account/api/spaces
# Click "Generate New Key"
# Name: ufe-reports-access
# Copy the Access Key and Secret Key
```

### 3. Set Environment Variables in App Platform

Go to your app: https://cloud.digitalocean.com/apps

Add these secrets:
- `SPACES_ACCESS_KEY` = Your Spaces access key
- `SPACES_SECRET_KEY` = Your Spaces secret key

The app will automatically redeploy.

### 4. Make Space Public (for downloads)

```bash
# Via dashboard:
# 1. Go to your Space → Settings
# 2. Under "File Listing" → Enable "List files"
# 3. Or set specific folder permissions

# Via CLI
doctl spaces configure ufe-reports --public-read
```

---

## How It Works

1. User requests report export via ADK web UI
2. App generates `.docx` file
3. File automatically uploads to: `https://ufe-reports.nyc3.digitaloceanspaces.com/reports/filename.docx`
4. Agent returns public download URL to user
5. User clicks link to download

---

## Alternative: Skip Spaces (local only)

If you don't set `SPACES_ACCESS_KEY` and `SPACES_SECRET_KEY`, files will only save locally to the container. **Not recommended** for production because:
- Files lost on container restart
- No way to download from App Platform
- Storage limited to container disk

---

## Testing

After setup, generate a report and check:

```bash
# List files in your Space
doctl spaces list-objects ufe-reports

# Download a file
curl -O https://ufe-reports.nyc3.digitaloceanspaces.com/reports/ufe_finance_report_20250112_123456.docx
```

---

## Security Notes

- Spaces keys have full access to your Space
- Consider using signed URLs for private reports (requires code changes)
- Monitor usage: https://cloud.digitalocean.com/spaces/ufe-reports

---

## Troubleshooting

**Files not uploading?**
```bash
# Check app logs
doctl apps logs YOUR_APP_ID --type run

# Look for "Failed to upload to Spaces" errors
```

**403 Forbidden when downloading?**
- Make sure Space has public-read permissions
- Check CORS settings if accessing from browser

**Wrong region?**
- Update `SPACES_REGION` env var in app spec
- Recreate Space in correct region
