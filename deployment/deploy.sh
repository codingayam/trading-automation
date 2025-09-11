#!/bin/bash
# Trading Automation Dashboard Deployment Script
# This script automates the deployment process for production environments

set -e  # Exit on any error

# Configuration
APP_NAME="trading-dashboard"
INTRADAY_NAME="trading-intraday"
SCHEDULER_NAME="trading-scheduler"
APP_USER="tradingapp"
APP_GROUP="tradingapp"
APP_DIR="/opt/trading-automation"
NGINX_CONFIG_PATH="/etc/nginx/sites-available/${APP_NAME}"
NGINX_ENABLED_PATH="/etc/nginx/sites-enabled/${APP_NAME}"
SYSTEMD_DASHBOARD_PATH="/etc/systemd/system/${APP_NAME}.service"
SYSTEMD_INTRADAY_PATH="/etc/systemd/system/${INTRADAY_NAME}.service"
SYSTEMD_SCHEDULER_PATH="/etc/systemd/system/${SCHEDULER_NAME}.service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
        exit 1
    fi
}

# Create application user
create_app_user() {
    log "Creating application user: $APP_USER"
    
    if id "$APP_USER" &>/dev/null; then
        warning "User $APP_USER already exists"
    else
        useradd --system --shell /bin/bash --home-dir "$APP_DIR" \
                --create-home --group-name "$APP_GROUP" "$APP_USER"
        success "User $APP_USER created"
    fi
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    apt-get update
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        nginx \
        supervisor \
        git \
        curl \
        build-essential \
        pkg-config
    
    success "System dependencies installed"
}

# Set up application directory
setup_app_directory() {
    log "Setting up application directory: $APP_DIR"
    
    # Create directories
    mkdir -p "$APP_DIR"/{logs,tmp,data}
    
    # Set ownership
    chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
    
    # Set permissions
    chmod 755 "$APP_DIR"
    chmod 775 "$APP_DIR"/{logs,tmp,data}
    
    success "Application directory set up"
}

# Deploy application code
deploy_application() {
    log "Deploying application code..."
    
    # Copy application files (assuming source is in current directory)
    if [[ ! -d "src" ]]; then
        error "Source directory not found. Run this script from the project root."
        exit 1
    fi
    
    # Copy files
    cp -r src/ config/ requirements*.txt main.py "$APP_DIR/"
    cp -r deployment/ "$APP_DIR/"
    
    # Create Python virtual environment
    log "Creating Python virtual environment..."
    sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
    
    # Install Python dependencies
    log "Installing Python dependencies..."
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install gunicorn
    
    # Set ownership
    chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
    
    success "Application deployed"
}

# Configure environment
configure_environment() {
    log "Configuring environment..."
    
    # Create .env file if it doesn't exist
    if [[ ! -f "$APP_DIR/.env" ]]; then
        log "Creating .env file..."
        cat > "$APP_DIR/.env" << EOF
# Environment Configuration
ENVIRONMENT=production

# Database
DATABASE_PATH=data/trading_automation.db
DATABASE_BACKUP_ENABLED=true

# Dashboard
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=5000
DASHBOARD_DEBUG=false

# Logging
LOG_LEVEL=INFO
LOG_PATH=logs

# API Keys (CONFIGURE THESE!)
QUIVER_API_KEY=your_quiver_api_key_here
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
ALPACA_PAPER=true

# Andy Grok Agent Configuration
ANDY_GROK_ENABLED=true
RSI_PERIOD=14
RSI_OVERSOLD_THRESHOLD=30.0
RSI_OVERBOUGHT_THRESHOLD=70.0

# Security
FLASK_SECRET_KEY=$(openssl rand -base64 32)
EOF
        chown "$APP_USER:$APP_GROUP" "$APP_DIR/.env"
        chmod 600 "$APP_DIR/.env"
        
        warning "Created .env file with default values. Please update API keys!"
    fi
    
    success "Environment configured"
}

# Initialize database
init_database() {
    log "Initializing database..."
    
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" -c "
import sys
sys.path.insert(0, '$APP_DIR')
from src.data.database import initialize_database
if initialize_database():
    print('Database initialized successfully')
else:
    print('Database initialization failed')
    sys.exit(1)
"
    
    success "Database initialized"
}

# Configure Nginx
configure_nginx() {
    log "Configuring Nginx..."
    
    # Copy Nginx configuration
    sed "s|/path/to/trading-automation|$APP_DIR|g" \
        "$APP_DIR/deployment/nginx.conf" > "$NGINX_CONFIG_PATH"
    
    # Enable site
    ln -sf "$NGINX_CONFIG_PATH" "$NGINX_ENABLED_PATH"
    
    # Remove default site if it exists
    if [[ -f "/etc/nginx/sites-enabled/default" ]]; then
        rm -f "/etc/nginx/sites-enabled/default"
    fi
    
    # Test Nginx configuration
    nginx -t
    
    success "Nginx configured"
}

# Configure systemd services
configure_systemd() {
    log "Configuring systemd services..."
    
    # Configure dashboard service
    sed -e "s|/path/to/trading-automation|$APP_DIR|g" \
        -e "s|User=tradingapp|User=$APP_USER|g" \
        -e "s|Group=tradingapp|Group=$APP_GROUP|g" \
        "$APP_DIR/deployment/systemd/trading-dashboard.service" > "$SYSTEMD_DASHBOARD_PATH"
    
    # Configure intraday scheduler service (Andy Grok Agent)
    sed -e "s|/path/to/trading-automation|$APP_DIR|g" \
        -e "s|User=tradingapp|User=$APP_USER|g" \
        -e "s|Group=tradingapp|Group=$APP_GROUP|g" \
        "$APP_DIR/deployment/systemd/trading-intraday.service" > "$SYSTEMD_INTRADAY_PATH"
    
    # Configure daily scheduler service (Congressional trades)
    sed -e "s|/path/to/trading-automation|$APP_DIR|g" \
        -e "s|User=tradingapp|User=$APP_USER|g" \
        -e "s|Group=tradingapp|Group=$APP_GROUP|g" \
        "$APP_DIR/deployment/systemd/trading-scheduler.service" > "$SYSTEMD_SCHEDULER_PATH"
    
    # Reload systemd
    systemctl daemon-reload
    
    success "Systemd services configured"
}

# Start services
start_services() {
    log "Starting services..."
    
    # Enable and start dashboard service
    systemctl enable "$APP_NAME"
    systemctl start "$APP_NAME"
    
    # Enable and start intraday scheduler (Andy Grok Agent)
    systemctl enable "$INTRADAY_NAME"
    systemctl start "$INTRADAY_NAME"
    
    # Enable and start daily scheduler (Congressional trades)
    systemctl enable "$SCHEDULER_NAME"
    systemctl start "$SCHEDULER_NAME"
    
    # Restart Nginx
    systemctl restart nginx
    systemctl enable nginx
    
    success "Services started"
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Check dashboard service status
    if systemctl is-active --quiet "$APP_NAME"; then
        success "Dashboard service is running"
    else
        error "Dashboard service is not running"
        systemctl status "$APP_NAME"
        return 1
    fi
    
    # Check intraday scheduler status
    if systemctl is-active --quiet "$INTRADAY_NAME"; then
        success "Intraday scheduler (Andy Grok) is running"
    else
        error "Intraday scheduler is not running"
        systemctl status "$INTRADAY_NAME"
        return 1
    fi
    
    # Check daily scheduler status
    if systemctl is-active --quiet "$SCHEDULER_NAME"; then
        success "Daily scheduler is running"
    else
        error "Daily scheduler is not running"
        systemctl status "$SCHEDULER_NAME"
        return 1
    fi
    
    # Check Nginx status
    if systemctl is-active --quiet nginx; then
        success "Nginx is running"
    else
        error "Nginx is not running"
        systemctl status nginx
        return 1
    fi
    
    # Test HTTP response
    log "Testing HTTP response..."
    sleep 5  # Give services time to start
    
    if curl -f -s "http://localhost/api/health" > /dev/null; then
        success "Dashboard is responding to HTTP requests"
    else
        error "Dashboard is not responding to HTTP requests"
        return 1
    fi
    
    success "Deployment verified successfully!"
}

# Show deployment information
show_info() {
    echo ""
    echo "==============================================="
    echo "  DEPLOYMENT COMPLETED SUCCESSFULLY"
    echo "==============================================="
    echo ""
    echo "Application Directory: $APP_DIR"
    echo "Service Name: $APP_NAME"
    echo "Application User: $APP_USER"
    echo ""
    echo "Useful Commands:"
    echo "  sudo systemctl status $APP_NAME"
    echo "  sudo systemctl status $INTRADAY_NAME" 
    echo "  sudo systemctl status $SCHEDULER_NAME"
    echo "  sudo systemctl restart $APP_NAME"
    echo "  sudo systemctl restart $INTRADAY_NAME"
    echo "  sudo systemctl restart $SCHEDULER_NAME" 
    echo "  sudo journalctl -u $INTRADAY_NAME -f  # Follow Andy Grok logs"
    echo "  sudo nginx -t"
    echo "  sudo systemctl reload nginx"
    echo ""
    echo "Configuration Files:"
    echo "  Environment: $APP_DIR/.env"
    echo "  Nginx: $NGINX_CONFIG_PATH"
    echo "  Systemd: $SYSTEMD_SERVICE_PATH"
    echo ""
    echo "Log Files:"
    echo "  Application: $APP_DIR/logs/"
    echo "  Nginx: /var/log/nginx/"
    echo "  Systemd: journalctl -u $APP_NAME"
    echo ""
    warning "Remember to:"
    warning "1. Update API keys in $APP_DIR/.env"
    warning "2. Configure your domain in $NGINX_CONFIG_PATH"
    warning "3. Set up SSL certificates for production"
    warning "4. Configure firewall rules"
    echo ""
}

# Main deployment process
main() {
    log "Starting Trading Automation Dashboard deployment..."
    
    check_root
    create_app_user
    install_dependencies
    setup_app_directory
    deploy_application
    configure_environment
    init_database
    configure_nginx
    configure_systemd
    start_services
    
    if verify_deployment; then
        show_info
        exit 0
    else
        error "Deployment verification failed"
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    "install")
        main
        ;;
    "update")
        log "Updating application..."
        deploy_application
        systemctl restart "$APP_NAME"
        systemctl reload nginx
        verify_deployment
        ;;
    "uninstall")
        log "Uninstalling application..."
        systemctl stop "$APP_NAME" 2>/dev/null || true
        systemctl disable "$APP_NAME" 2>/dev/null || true
        rm -f "$SYSTEMD_SERVICE_PATH"
        rm -f "$NGINX_ENABLED_PATH"
        systemctl daemon-reload
        systemctl restart nginx
        userdel "$APP_USER" 2>/dev/null || true
        rm -rf "$APP_DIR"
        success "Application uninstalled"
        ;;
    *)
        echo "Usage: $0 {install|update|uninstall}"
        echo ""
        echo "Commands:"
        echo "  install   - Full installation and configuration"
        echo "  update    - Update application code and restart services"
        echo "  uninstall - Remove application and configuration"
        exit 1
        ;;
esac