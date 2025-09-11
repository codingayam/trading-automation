# Deployment Guide - Trading Automation System

## Overview

This guide covers the complete deployment process for the Trading Automation System, including development, staging, and production environments.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Monitoring & Alerting](#monitoring--alerting)
- [Security Configuration](#security-configuration)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │   Dashboard     │    │  Trading App    │
│  Load Balancer  │◄──►│   (Flask)       │◄──►│   (Python)      │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Redis       │◄──►│   PostgreSQL    │    │  External APIs  │
│   (Caching)     │    │   (Database)    │    │ Alpaca/Quiver   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Monitoring    │
                       │ Prometheus      │
                       │ Grafana         │
                       └─────────────────┘
```

### Data Flow

1. **Data Ingestion**: Quiver API → Congressional Trading Data
2. **Processing**: Trading Agents → Decision Making
3. **Execution**: Alpaca API → Trade Orders
4. **Storage**: PostgreSQL → Persistence
5. **Visualization**: Dashboard → User Interface
6. **Monitoring**: Prometheus/Grafana → System Health

## Prerequisites

### System Requirements

**Minimum Production Requirements:**
- **OS**: Ubuntu 20.04 LTS or CentOS 8
- **RAM**: 8GB minimum, 16GB recommended
- **CPU**: 4 cores minimum, 8 cores recommended
- **Storage**: 100GB SSD minimum
- **Network**: Stable internet connection with low latency

**Development Requirements:**
- Python 3.9+
- Docker 20.10+
- Docker Compose 1.29+
- Git 2.30+

### External Dependencies

- **Alpaca Markets Account**: Paper trading or live trading
- **Quiver Quantitative API**: Congressional trading data access
- **Domain & SSL Certificate**: For production HTTPS access

## Environment Setup

### Development Environment

```bash
# Clone repository
git clone <repository-url>
cd trading-automation

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Environment Variables

Create `.env` file with required configuration:

```bash
# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO

# Database Configuration
DATABASE_URL=postgresql://tradingapp:password@localhost:5432/trading_automation
REDIS_URL=redis://localhost:6379/0

# API Keys
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
ALPACA_PAPER=true  # Set to false for live trading
QUIVER_API_KEY=your_quiver_api_key

# Security
SECRET_KEY=your-secret-key-here
FLASK_SECRET_KEY=your-flask-secret-key

# Monitoring
GRAFANA_PASSWORD=secure_password
PROMETHEUS_RETENTION=30d

# Email Alerts (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

## Docker Deployment

### Development with Docker

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production with Docker

```bash
# Build production images
docker-compose -f docker-compose.production.yml build

# Start production services
docker-compose -f docker-compose.production.yml up -d

# Verify deployment
docker-compose -f docker-compose.production.yml ps
```

### Docker Services

| Service | Port | Description |
|---------|------|-------------|
| nginx | 80, 443 | Web server & reverse proxy |
| dashboard | 8000 | Flask web application |
| trading-app | 5000 | Core trading application |
| postgres | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache |
| prometheus | 9090 | Metrics collection |
| grafana | 3000 | Monitoring dashboards |

## Production Deployment

### Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create application directory
sudo mkdir -p /opt/trading-automation
sudo chown $USER:$USER /opt/trading-automation
```

### Automated Deployment

Use the provided deployment script:

```bash
# Make deployment script executable
chmod +x deployment/deploy.sh

# Run deployment (requires sudo)
sudo ./deployment/deploy.sh
```

The deployment script handles:
- System user creation
- Directory structure setup
- Service configuration
- SSL certificate installation
- Firewall configuration
- Systemd service setup

### Manual Deployment Steps

1. **Database Setup**:
```bash
# Create PostgreSQL database
sudo -u postgres createdb trading_automation
sudo -u postgres createuser tradingapp
sudo -u postgres psql -c "ALTER USER tradingapp WITH PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE trading_automation TO tradingapp;"
```

2. **SSL Configuration**:
```bash
# Install Certbot for Let's Encrypt
sudo apt install certbot python3-certbot-nginx

# Generate SSL certificate
sudo certbot --nginx -d yourdomain.com
```

3. **Service Configuration**:
```bash
# Copy systemd service file
sudo cp deployment/systemd/trading-dashboard.service /etc/systemd/system/

# Enable and start service
sudo systemctl enable trading-dashboard
sudo systemctl start trading-dashboard
```

### Environment-Specific Configuration

**Staging Environment:**
```bash
export ENVIRONMENT=staging
export ALPACA_PAPER=true
export LOG_LEVEL=DEBUG
```

**Production Environment:**
```bash
export ENVIRONMENT=production
export ALPACA_PAPER=false  # Only if using live trading
export LOG_LEVEL=INFO
```

## Monitoring & Alerting

### Prometheus Configuration

Metrics collection configured in `deployment/prometheus/prometheus.yml`:

- **Application Metrics**: Custom business metrics
- **System Metrics**: CPU, memory, disk usage
- **Database Metrics**: PostgreSQL performance
- **API Metrics**: External API response times

### Grafana Dashboards

Pre-configured dashboards in `deployment/grafana/dashboards/`:

1. **System Overview**: Infrastructure metrics
2. **Application Performance**: Trading system metrics
3. **Business Metrics**: Trading performance and decisions
4. **Alert Status**: Current alerts and their status

### Alert Rules

Configured in `deployment/prometheus/alerts.yml`:

**Critical Alerts:**
- Application downtime
- Database connection failures
- Trading execution failures
- Account balance critically low

**Warning Alerts:**
- High resource usage
- Slow API responses
- API rate limit hits
- No trades processed in 24h

### Notification Setup

Configure alert notifications in Grafana:

1. **Email Notifications**: SMTP configuration
2. **Slack Integration**: Webhook URL
3. **PagerDuty**: For critical alerts
4. **Discord/Teams**: Team notifications

## Security Configuration

### Network Security

```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### Application Security

1. **Environment Variables**: Never commit secrets to git
2. **API Key Rotation**: Regular rotation of API keys
3. **Database Security**: Strong passwords, limited access
4. **SSL/TLS**: HTTPS only in production
5. **Access Control**: Role-based dashboard access

### Docker Security

```dockerfile
# Use non-root user
RUN groupadd --system tradingapp && \
    useradd --system --group tradingapp tradingapp
USER tradingapp

# Read-only root filesystem
--read-only --tmpfs /tmp:rw,noexec,nosuid,size=100m
```

### Security Checklist

- [ ] All secrets stored in environment variables
- [ ] Database access restricted by IP
- [ ] SSL certificates configured and auto-renewing
- [ ] Firewall configured with minimal open ports
- [ ] Regular security updates scheduled
- [ ] API keys stored securely and rotated regularly
- [ ] Application runs as non-root user
- [ ] Logs don't contain sensitive information

## Backup & Recovery

### Database Backup

```bash
#!/bin/bash
# Automated database backup script

BACKUP_DIR="/opt/backups/database"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="trading_automation_${DATE}.sql"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create database backup
pg_dump -h localhost -U tradingapp trading_automation > $BACKUP_DIR/$BACKUP_FILE

# Compress backup
gzip $BACKUP_DIR/$BACKUP_FILE

# Remove backups older than 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

### Configuration Backup

```bash
# Backup configuration files
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
    /opt/trading-automation/.env \
    /opt/trading-automation/docker-compose.production.yml \
    /etc/nginx/sites-available/trading-dashboard \
    /etc/systemd/system/trading-dashboard.service
```

### Recovery Procedures

**Database Recovery:**
```bash
# Stop application
sudo systemctl stop trading-dashboard

# Restore database
gunzip -c backup_file.sql.gz | psql -h localhost -U tradingapp trading_automation

# Start application
sudo systemctl start trading-dashboard
```

**Complete System Recovery:**
```bash
# Restore from backup server
rsync -av backup-server:/backups/trading-automation/ /opt/trading-automation/

# Restore database
./scripts/restore_database.sh latest_backup.sql.gz

# Restart services
docker-compose -f docker-compose.production.yml up -d
```

## Troubleshooting

### Common Issues

**Application Won't Start:**
```bash
# Check logs
docker-compose logs trading-app
sudo journalctl -u trading-dashboard

# Check configuration
docker-compose config

# Verify environment variables
env | grep -E "(ALPACA|QUIVER|DATABASE)"
```

**Database Connection Issues:**
```bash
# Test database connection
psql -h localhost -U tradingapp trading_automation

# Check PostgreSQL status
sudo systemctl status postgresql

# View PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

**High Memory Usage:**
```bash
# Check memory usage
free -h
docker stats

# Restart services to free memory
docker-compose restart
```

**SSL Certificate Issues:**
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Test SSL configuration
openssl s_client -connect yourdomain.com:443
```

### Log Locations

**Docker Logs:**
```bash
# Application logs
docker-compose logs -f trading-app
docker-compose logs -f dashboard

# System logs
journalctl -u docker
```

**System Logs:**
```bash
# Application logs
/opt/trading-automation/logs/
/var/log/nginx/
/var/log/postgresql/

# System logs
/var/log/syslog
/var/log/auth.log
```

### Performance Monitoring

**Real-time Monitoring:**
```bash
# System resources
htop
iotop
nethogs

# Docker resources
docker stats

# Database performance
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"
```

### Health Checks

**Application Health:**
```bash
# Check all services
curl -f http://localhost/health

# Individual service checks
curl -f http://localhost:5000/health    # Trading app
curl -f http://localhost:8000/health    # Dashboard
```

**Database Health:**
```bash
# PostgreSQL status
sudo systemctl status postgresql

# Connection test
pg_isready -h localhost -p 5432
```

**External API Health:**
```bash
# Test API connectivity
curl -H "Authorization: Bearer $QUIVER_API_KEY" \
    "https://api.quiverquant.com/beta/bulk/congresstrading"

curl -H "APCA-API-KEY-ID: $ALPACA_API_KEY" \
    -H "APCA-API-SECRET-KEY: $ALPACA_SECRET_KEY" \
    "https://paper-api.alpaca.markets/v2/account"
```

## Scaling Considerations

### Horizontal Scaling

1. **Load Balancer**: Multiple application instances behind Nginx
2. **Database Replication**: Read replicas for dashboard queries
3. **Redis Clustering**: Distributed caching
4. **Container Orchestration**: Kubernetes for auto-scaling

### Vertical Scaling

1. **Resource Allocation**: Increase CPU/memory for containers
2. **Database Optimization**: Query optimization and indexing
3. **Connection Pooling**: Efficient database connection management

### Performance Optimization

1. **Caching Strategy**: Redis for frequently accessed data
2. **Database Indexing**: Optimize query performance
3. **Background Jobs**: Async processing for heavy operations
4. **CDN Integration**: Static asset delivery optimization