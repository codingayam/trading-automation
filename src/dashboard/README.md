# Trading Automation Dashboard

A comprehensive web-based dashboard for monitoring and managing automated trading agents that follow congressional trading activities.

## Features

### Overview Dashboard
- **Real-time agent performance monitoring** with auto-refresh every 60 seconds during market hours
- **Portfolio value tracking** with formatted currency display
- **Daily and total return calculations** with color-coded performance indicators
- **Market status indicator** showing current market state (open/closed/weekend/holiday)
- **Responsive design** that works on desktop and tablet devices
- **Connection status monitoring** with automatic retry on failures

### Individual Agent Dashboard  
- **Detailed position tracking** showing current holdings for each agent
- **Performance metrics** including daily returns, since-open returns, and unrealized P&L
- **Portfolio weight calculations** showing percentage of total portfolio value
- **Real-time price updates** using cached market data (15-minute refresh)
- **Sortable position tables** by ticker, amount, return, etc.
- **Politicians tracking display** showing which congress members are being followed

### REST API
- **GET /api/agents** - List all agents with performance summary
- **GET /api/agents/{agent_id}** - Detailed agent information
- **GET /api/agents/{agent_id}/positions** - Current positions for agent
- **GET /api/agents/{agent_id}/performance** - Performance history
- **GET /api/health** - System health check
- **GET /api/system/status** - System status and last update time

## Architecture

### Backend Components
- **Flask web framework** with CORS support for API endpoints
- **SQLite database integration** using the existing database schema
- **Market data service** integration for real-time price updates
- **Caching layer** with 15-minute refresh for market data optimization
- **Error handling** with structured exceptions and retry mechanisms
- **Performance monitoring** with execution time tracking

### Frontend Components
- **Vanilla JavaScript** with modern ES6+ features (no external frameworks)
- **CSS Grid and Flexbox** for responsive layouts
- **Auto-refresh functionality** with market hours detection
- **Connection monitoring** with offline/online status tracking
- **Loading states** and error handling with user feedback
- **Accessibility features** including ARIA labels and keyboard navigation

### Security Features
- **CORS configuration** for cross-origin request handling
- **Input validation** and parameter sanitization
- **Error message sanitization** to prevent information disclosure
- **Rate limiting support** via Nginx configuration
- **Security headers** including XSS protection and content type options

## Quick Start

### Development Mode

1. **Start the development server:**
   ```bash
   cd src/dashboard
   python run_dashboard.py
   ```

2. **Access the dashboard:**
   - Overview: http://localhost:5000
   - Individual agent: http://localhost:5000/agent/{agent_id}
   - API health: http://localhost:5000/api/health

### Testing

1. **Run integration tests:**
   ```bash
   cd src/dashboard  
   python test_dashboard.py
   ```

2. **Test specific API endpoints:**
   ```bash
   curl http://localhost:5000/api/health
   curl http://localhost:5000/api/agents
   curl http://localhost:5000/api/agents/josh_gottheimer
   ```

## Production Deployment

### Prerequisites
- Ubuntu/Debian server with sudo access
- Python 3.8+ installed
- Domain name configured (optional but recommended)

### Automated Deployment

1. **Run the deployment script:**
   ```bash
   sudo ./deployment/deploy.sh install
   ```

2. **Configure API keys:**
   ```bash
   sudo nano /opt/trading-automation/.env
   # Update QUIVER_API_KEY and ALPACA_API_KEY
   ```

3. **Update domain configuration:**
   ```bash
   sudo nano /etc/nginx/sites-available/trading-dashboard
   # Update server_name directive
   ```

4. **Restart services:**
   ```bash
   sudo systemctl restart trading-dashboard
   sudo systemctl reload nginx
   ```

### Manual Deployment

1. **Install system dependencies:**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv nginx supervisor
   ```

2. **Create application user:**
   ```bash
   sudo useradd --system --shell /bin/bash --home-dir /opt/trading-automation \
                --create-home tradingapp
   ```

3. **Deploy application:**
   ```bash
   sudo cp -r src/ config/ requirements*.txt /opt/trading-automation/
   sudo chown -R tradingapp:tradingapp /opt/trading-automation/
   ```

4. **Set up Python environment:**
   ```bash
   sudo -u tradingapp python3 -m venv /opt/trading-automation/venv
   sudo -u tradingapp /opt/trading-automation/venv/bin/pip install -r requirements.txt
   sudo -u tradingapp /opt/trading-automation/venv/bin/pip install gunicorn
   ```

5. **Configure services:**
   ```bash
   sudo cp deployment/systemd/trading-dashboard.service /etc/systemd/system/
   sudo cp deployment/nginx.conf /etc/nginx/sites-available/trading-dashboard
   sudo ln -s /etc/nginx/sites-available/trading-dashboard /etc/nginx/sites-enabled/
   sudo systemctl daemon-reload
   ```

6. **Start services:**
   ```bash
   sudo systemctl enable trading-dashboard
   sudo systemctl start trading-dashboard
   sudo systemctl restart nginx
   ```

## Configuration

### Environment Variables
```bash
# Dashboard settings
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=5000
DASHBOARD_DEBUG=false

# Database
DATABASE_PATH=data/trading_automation.db

# API Keys
QUIVER_API_KEY=your_key_here
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_key_here

# Security
FLASK_SECRET_KEY=your_secret_key_here
```

### Agent Configuration
Agents are configured in `config/agents.json`:
```json
{
  "agents": [
    {
      "id": "josh_gottheimer",
      "name": "Josh Gottheimer Agent",
      "type": "individual",
      "politicians": ["Josh Gottheimer"],
      "enabled": true
    }
  ]
}
```

## Monitoring and Maintenance

### Service Management
```bash
# Check status
sudo systemctl status trading-dashboard
sudo systemctl status nginx

# View logs
sudo journalctl -u trading-dashboard -f
tail -f /var/log/nginx/dashboard_access.log

# Restart services
sudo systemctl restart trading-dashboard
sudo systemctl reload nginx
```

### Performance Monitoring
- **API response times** are logged and tracked
- **Database query performance** is monitored
- **Market data cache hit rates** are recorded
- **System resource usage** is tracked via health endpoint

### Database Maintenance
```bash
# Backup database
cp /opt/trading-automation/data/trading_automation.db /backup/location/

# Check database integrity
sqlite3 /opt/trading-automation/data/trading_automation.db "PRAGMA integrity_check;"

# Vacuum database (optimize)
sqlite3 /opt/trading-automation/data/trading_automation.db "VACUUM;"
```

## Troubleshooting

### Common Issues

1. **Dashboard not loading:**
   - Check service status: `sudo systemctl status trading-dashboard`
   - Check logs: `sudo journalctl -u trading-dashboard`
   - Verify port availability: `sudo netstat -tlnp | grep :5000`

2. **API endpoints returning 500 errors:**
   - Check database connectivity
   - Verify environment variables are set
   - Check application logs for specific error messages

3. **Static files not loading (CSS/JS):**
   - Verify Nginx configuration
   - Check file permissions: `ls -la /opt/trading-automation/src/dashboard/static/`
   - Test Nginx config: `sudo nginx -t`

4. **Market data not updating:**
   - Check internet connectivity
   - Verify API keys are configured
   - Check market data service logs

### Debug Mode

Enable debug mode for development:
```bash
export DASHBOARD_DEBUG=true
python src/dashboard/run_dashboard.py
```

## API Documentation

### Authentication
No authentication is required for the MVP version. In production, consider adding:
- API key authentication
- Rate limiting
- IP whitelisting

### Response Format
All API responses follow this format:
```json
{
  "data": { ... },
  "timestamp": "2024-01-01T12:00:00Z",
  "status": "success"
}
```

Error responses:
```json
{
  "error": "Error description",
  "code": "ERROR_CODE",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Rate Limiting
- API endpoints: 10 requests/second per IP
- Dashboard pages: 5 requests/second per IP
- Burst allowance: 20 requests for API, 10 for dashboard

## Security Considerations

### Production Security Checklist
- [ ] Configure HTTPS with SSL certificates
- [ ] Update default secret keys
- [ ] Configure firewall rules
- [ ] Set up log rotation
- [ ] Configure automated backups
- [ ] Monitor for security vulnerabilities
- [ ] Implement API authentication (if needed)
- [ ] Configure fail2ban for brute force protection

### Data Privacy
- No sensitive personal data is stored
- Only public congressional trading data is processed
- API keys are stored as environment variables
- Database contains only trading positions and performance metrics

## Performance Optimization

### Caching Strategy
- **Market data**: 15-minute cache for price information
- **API responses**: 5-15 minute cache based on endpoint
- **Static files**: 1-year browser cache with immutable headers
- **Database queries**: Optimized with proper indexing

### Load Testing
Use tools like Apache Bench or wrk to test performance:
```bash
# Test API endpoint
ab -n 1000 -c 10 http://localhost:5000/api/agents

# Test dashboard page
ab -n 100 -c 5 http://localhost:5000/
```

### Scaling Considerations
- **Horizontal scaling**: Add more Gunicorn workers
- **Load balancing**: Use Nginx upstream for multiple app servers  
- **Database**: Consider PostgreSQL for high-traffic deployments
- **CDN**: Use CloudFlare or similar for static asset delivery

## Contributing

### Development Setup
1. Install development dependencies: `pip install -r requirements-dev.txt`
2. Run tests: `python src/dashboard/test_dashboard.py`
3. Start development server: `python src/dashboard/run_dashboard.py`
4. Access dashboard at http://localhost:5000

### Code Style
- Follow PEP 8 for Python code
- Use ESLint for JavaScript code
- Write comprehensive docstrings
- Include unit tests for new features

### Testing
- Write integration tests for API endpoints
- Test responsive design on multiple devices
- Validate accessibility with screen readers
- Performance test with realistic data volumes