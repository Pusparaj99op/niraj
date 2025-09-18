#!/bin/bash

# NIRAJ Deployment Script
# Handles deployment to production environment

set -e

echo "🚀 NIRAJ Production Deployment"
echo "==============================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Configuration
DEPLOY_ENV="${1:-production}"
DEPLOY_DIR="/opt/niraj"
SERVICE_NAME="niraj"
BACKUP_DIR="/opt/niraj/backups"

# Pre-deployment checks
check_environment() {
    log_info "Checking deployment environment..."
    
    # Check if running as root or with sudo
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root - ensure this is intentional"
    fi
    
    # Check environment variables
    required_vars=(
        "DATABASE_URL"
        "REDIS_URL" 
        "JWT_SECRET_KEY"
        "OLLAMA_BASE_URL"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    log_success "Environment checks passed"
}

# Build application
build_app() {
    log_info "Building application..."
    
    # Build backend (no build step needed for Python)
    log_info "Preparing backend..."
    cd backend
    poetry install --only=main --no-dev
    cd ..
    
    # Build frontend
    log_info "Building frontend..."
    cd frontend
    npm ci --production
    npm run build
    cd ..
    
    log_success "Application built successfully"
}

# Deploy application
deploy_app() {
    log_info "Deploying application to $DEPLOY_DIR..."
    
    # Create deployment directory
    sudo mkdir -p "$DEPLOY_DIR"
    sudo mkdir -p "$BACKUP_DIR"
    
    # Backup current deployment if exists
    if [[ -d "$DEPLOY_DIR/backend" ]]; then
        log_info "Creating backup of current deployment..."
        sudo tar -czf "$BACKUP_DIR/niraj-backup-$(date +%Y%m%d-%H%M%S).tar.gz" -C "$DEPLOY_DIR" .
    fi
    
    # Copy application files
    log_info "Copying application files..."
    sudo cp -r backend "$DEPLOY_DIR/"
    sudo cp -r frontend/dist "$DEPLOY_DIR/frontend"
    sudo cp -r scripts "$DEPLOY_DIR/"
    
    # Set permissions
    sudo chown -R $USER:$USER "$DEPLOY_DIR"
    sudo chmod +x "$DEPLOY_DIR/scripts"/*.sh
    
    log_success "Application deployed"
}

# Configure system service
setup_service() {
    log_info "Setting up system service..."
    
    # Create systemd service file
    sudo tee "/etc/systemd/system/$SERVICE_NAME.service" > /dev/null << EOF
[Unit]
Description=NIRAJ Trading System
After=network.target redis.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$DEPLOY_DIR/backend
Environment=PATH=$DEPLOY_DIR/backend/.venv/bin
ExecStart=$DEPLOY_DIR/backend/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    
    log_success "System service configured"
}

# Setup reverse proxy (Nginx)
setup_nginx() {
    log_info "Setting up Nginx reverse proxy..."
    
    sudo tee "/etc/nginx/sites-available/$SERVICE_NAME" > /dev/null << EOF
server {
    listen 80;
    server_name your-domain.com;  # Change this to your domain
    
    # Frontend
    location / {
        root $DEPLOY_DIR/frontend;
        try_files \$uri \$uri/ /index.html;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF
    
    # Enable site
    sudo ln -sf "/etc/nginx/sites-available/$SERVICE_NAME" "/etc/nginx/sites-enabled/"
    sudo nginx -t && sudo systemctl reload nginx
    
    log_success "Nginx configured"
}

# Database migration
migrate_database() {
    log_info "Running database migrations..."
    
    cd "$DEPLOY_DIR"
    ./scripts/db_manager.sh migrate
    
    log_success "Database migrations completed"
}

# Start services
start_services() {
    log_info "Starting services..."
    
    # Start NIRAJ service
    sudo systemctl start "$SERVICE_NAME"
    sudo systemctl status "$SERVICE_NAME" --no-pager
    
    # Verify service is running
    sleep 3
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "NIRAJ service started successfully"
    else
        log_error "NIRAJ service failed to start"
        sudo journalctl -u "$SERVICE_NAME" --no-pager -n 20
        exit 1
    fi
}

# Health check
health_check() {
    log_info "Running health checks..."
    
    # Check API endpoint
    if curl -f -s http://localhost:8000/api/v1/system/status > /dev/null; then
        log_success "API health check passed"
    else
        log_error "API health check failed"
        exit 1
    fi
    
    # Check database
    cd "$DEPLOY_DIR"
    ./scripts/db_manager.sh check
    
    log_success "All health checks passed"
}

# Rollback function
rollback() {
    log_warning "Rolling back deployment..."
    
    # Stop service
    sudo systemctl stop "$SERVICE_NAME"
    
    # Find latest backup
    latest_backup=$(ls -t "$BACKUP_DIR"/niraj-backup-*.tar.gz | head -n1)
    
    if [[ -n "$latest_backup" ]]; then
        log_info "Restoring from backup: $latest_backup"
        sudo rm -rf "$DEPLOY_DIR"/{backend,frontend,scripts}
        sudo tar -xzf "$latest_backup" -C "$DEPLOY_DIR"
        sudo chown -R $USER:$USER "$DEPLOY_DIR"
        
        # Restart service
        sudo systemctl start "$SERVICE_NAME"
        log_success "Rollback completed"
    else
        log_error "No backup found for rollback"
        exit 1
    fi
}

# Main deployment function
main() {
    local operation="$1"
    
    case "$operation" in
        "deploy")
            check_environment
            build_app
            deploy_app
            setup_service
            migrate_database
            start_services
            health_check
            log_success "🎉 Deployment completed successfully!"
            ;;
        "rollback")
            rollback
            ;;
        "health")
            health_check
            ;;
        "nginx")
            setup_nginx
            ;;
        "service")
            setup_service
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [operation]"
            echo ""
            echo "Operations:"
            echo "  deploy   - Full deployment process"
            echo "  rollback - Rollback to previous version"
            echo "  health   - Run health checks"
            echo "  nginx    - Setup Nginx configuration"
            echo "  service  - Setup systemd service"
            echo "  help     - Show this help"
            echo ""
            echo "Environment variables required:"
            echo "  DATABASE_URL, REDIS_URL, JWT_SECRET_KEY, OLLAMA_BASE_URL"
            ;;
        *)
            log_error "Unknown operation: $operation"
            log_info "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"