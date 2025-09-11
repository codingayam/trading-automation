# Railway Deployment Setup

This guide explains how to configure environment variables for the trading automation system on Railway.

## Required Environment Variables

Configure these variables in your Railway project dashboard:

### 1. Alpaca Trading API
```
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
ALPACA_PAPER=true
```

### 2. Quiver Congressional Data API
```
QUIVER_API_KEY=your_quiver_api_key_here
```

### 3. Optional Configuration
```
ENVIRONMENT=production
DATABASE_PATH=data/trading_automation.db
DAILY_EXECUTION_TIME=21:30
TIMEZONE=US/Eastern
```

## How to Configure on Railway

1. **Go to your Railway project dashboard**
   - Visit https://railway.app
   - Select your trading-automation project

2. **Add environment variables**
   - Click on "Variables" tab
   - Click "Add Variable" for each required variable
   - Copy the values from your local `.env` file

3. **Deploy**
   - Railway will automatically redeploy when variables are added
   - Both scheduler and dashboard will start successfully

## Getting API Keys

### Alpaca API Keys
1. Sign up at https://alpaca.markets
2. Go to "Paper Trading" section
3. Generate API keys (keep ALPACA_PAPER=true for testing)

### Quiver API Key
1. Sign up at https://api.quiverquant.com
2. Get your API key from the dashboard
3. Add it as QUIVER_API_KEY

## Troubleshooting

- **Scheduler keeps crashing**: Check that all 4 required environment variables are set
- **Dashboard shows no data**: Ensure QUIVER_API_KEY is valid
- **No trades executing**: Verify ALPACA_API_KEY and ALPACA_SECRET_KEY are correct

## Monitoring

Once deployed, your system will be available at:
- **Dashboard**: https://your-app-name.up.railway.app/
- **API**: https://your-app-name.up.railway.app/api/agents

The scheduler runs automatically at 9:30 PM EST daily.