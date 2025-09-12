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

### 2. Database Configuration
The system uses SQLite database with persistent file storage.
No additional database service required - SQLite files are stored on the Railway volume.

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

### ✅ Unified Scheduler Service
- Runs `python main.py start`
- Executes ALL agents together during market hours (9:30 AM ET)
- Congressional and technical agents in single process

### ✅ Dashboard Service  
- Runs Flask web interface
- Accessible via Railway's public URL
- Shows trading performance and agent status

### ✅ Health Monitoring
- Health check endpoint at `/health`
- Automatic restart on failure
- Process monitoring via Supervisor

## Database Configuration

### SQLite with Persistent Storage
The system uses SQLite database stored on Railway volume:
- **File-based** - no separate database service needed
- **Persistent** - data survives deployments
- **Zero cost** - included with app service
- **Automatic** - no configuration required

## Service Architecture

```
Railway Service (Single Container)
├── Supervisor (Process Manager)
│   ├── Unified Scheduler Process (main.py start)
│   └── Dashboard Process (Flask app)
├── SQLite Database (file storage)
└── Health Check Endpoint
```

## Cost Estimate

- **App Service**: ~$5/month (minimal usage)
- **Database**: $0 (SQLite included)
- **Total**: ~$5/month

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
| `DATABASE_PATH` | Auto | `data/trading_automation.db` | SQLite database file path |
| `ALPACA_API_KEY` | Yes | - | Alpaca trading API key |
| `ALPACA_SECRET_KEY` | Yes | - | Alpaca trading secret |
| `ALPACA_PAPER` | No | `true` | Use paper trading |
| `QUIVER_API_KEY` | Yes | - | Quiver congressional data API |
| `LOG_LEVEL` | No | `INFO` | Logging level |

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

The system will execute all agents together during market hours (9:30 AM ET) and you can monitor everything through the web dashboard.