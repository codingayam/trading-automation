# Railway Deployment Guide 🚀

Deploy your trading automation system to Railway with a simplified all-in-one setup.

## Quick Start

### 1. Deploy from GitHub Repository
1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Connect your GitHub account if needed
5. Select your repository: `codingayam/trading-automation`
6. Choose the **main** branch
7. Railway will automatically detect `Dockerfile.railway` and start building

### 2. Add PostgreSQL Database
In your Railway project dashboard:
1. Click **"New Service"**
2. Select **"Database"** → **"PostgreSQL"**
3. Railway automatically sets the `DATABASE_URL` environment variable

### 3. Set Environment Variables
In Railway dashboard → your app service → **Variables** tab:

**Required:**
```
ENVIRONMENT=production
ALPACA_API_KEY=your_alpaca_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_here
ALPACA_PAPER=true
QUIVER_API_KEY=your_quiver_key_here
```

**Optional:**
```
LOG_LEVEL=INFO
DAILY_EXECUTION_TIME=21:30
```

### 4. Automatic Deployment
Railway will automatically:
- Build using `Dockerfile.railway`
- Start both the scheduler and dashboard
- Provide a public URL for the dashboard
- Redeploy whenever you push to GitHub

That's it! Your trading automation system is now deployed and running in the cloud! 🎉

## What Gets Deployed

The simplified Railway deployment includes:

### ✅ Scheduler Service
- Runs `python main.py scheduler`
- Executes daily at 9:30 PM EST
- Automatically handles agent execution

### ✅ Dashboard Service  
- Runs Flask web interface
- Accessible via Railway's public URL
- Shows trading performance and agent status

### ✅ Health Monitoring
- Health check endpoint at `/health`
- Automatic restart on failure
- Process monitoring via Supervisor

## Database Configuration

### PostgreSQL (Recommended)
Railway automatically provides PostgreSQL with these benefits:
- **Managed service** - no maintenance required
- **Automatic backups** - built-in backup system
- **Scalable** - can grow with your needs
- **$5/month** - cost-effective for production

The `DATABASE_URL` is automatically configured by Railway.

## Service Architecture

```
Railway Service (Single Container)
├── Supervisor (Process Manager)
│   ├── Scheduler Process (main.py scheduler)
│   └── Dashboard Process (Flask app)
├── PostgreSQL Database (Railway managed)
└── Health Check Endpoint
```

## Cost Estimate

- **App Service**: ~$5/month (minimal usage)
- **PostgreSQL**: $5/month
- **Total**: ~$10/month

## Monitoring & Logs

### View Logs
```bash
railway logs
```

### Service Status
```bash
railway status
```

### Dashboard Access
Your dashboard will be available at:
`https://your-app-name.up.railway.app`

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | Yes | `production` | Environment mode |
| `DATABASE_URL` | Auto | - | PostgreSQL connection (auto-set) |
| `ALPACA_API_KEY` | Yes | - | Alpaca trading API key |
| `ALPACA_SECRET_KEY` | Yes | - | Alpaca trading secret |
| `ALPACA_PAPER` | No | `true` | Use paper trading |
| `QUIVER_API_KEY` | Yes | - | Quiver congressional data API |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `DAILY_EXECUTION_TIME` | No | `21:30` | Daily execution time (EST) |

## Troubleshooting

### Build Fails
```bash
# Check build logs
railway logs --build

# Common fixes:
# 1. Ensure all files are committed to git
# 2. Check Dockerfile.railway exists
# 3. Verify requirements.txt is complete
```

### Service Won't Start
```bash
# Check runtime logs
railway logs

# Common issues:
# 1. Missing environment variables
# 2. Database connection issues
# 3. Port configuration problems
```

### Database Connection Issues
```bash
# Verify DATABASE_URL is set
railway variables

# Check PostgreSQL service status
railway status
```

### Health Check Failures
The health check hits `/health` endpoint. If failing:
1. Check if dashboard service is running
2. Verify supervisor configuration
3. Check application logs

## Scaling & Performance

### Single Service Setup
- **Pros**: Simple, cost-effective, easy to manage
- **Cons**: Limited scalability, shared resources
- **Best for**: Personal use, small portfolios

### When to Consider Multi-Service
Scale to multiple services when you need:
- High availability
- Resource isolation
- Multiple environments
- Complex monitoring

## Security Notes

1. **Paper Trading**: Always start with `ALPACA_PAPER=true`
2. **API Keys**: Never commit keys to git
3. **Environment Variables**: Set sensitive data via Railway dashboard
4. **Database**: Railway PostgreSQL includes SSL by default

## Next Steps

After deployment:

1. **Verify Health**: Check `https://your-app.up.railway.app/health`
2. **View Dashboard**: Browse to your Railway URL
3. **Monitor Logs**: Use `railway logs` to watch execution
4. **Test Trading**: Ensure paper trading works before going live

## Support

- **Railway Issues**: [Railway Help Center](https://help.railway.app/)
- **App Issues**: Check application logs with `railway logs`
- **Trading Issues**: Verify API keys and paper trading mode

---

🎯 **Your trading automation system is now running in the cloud!** 

The system will execute daily at 9:30 PM EST and you can monitor everything through the web dashboard.