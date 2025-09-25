# NIRAJ Deployment & Operations Guide

## Overview

This guide covers the complete deployment, monitoring, and operational procedures for the NIRAJ trading system across development, staging, and production environments.

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Development Deployment](#development-deployment)
3. [Staging Deployment](#staging-deployment)
4. [Production Deployment](#production-deployment)
5. [Docker Deployment](#docker-deployment)
6. [Kubernetes Deployment](#kubernetes-deployment)
7. [Database Management](#database-management)
8. [Monitoring & Alerting](#monitoring--alerting)
9. [Backup & Recovery](#backup--recovery)
10. [Security Hardening](#security-hardening)
11. [Performance Tuning](#performance-tuning)
12. [Troubleshooting](#troubleshooting)
13. [Maintenance Procedures](#maintenance-procedures)

---

## Environment Setup

### System Requirements

#### Minimum Requirements (Development)
- **OS**: Ubuntu 22.04 LTS, macOS 12+, Windows 11 (WSL2)
- **CPU**: 4 cores, 2.5GHz+
- **RAM**: 8GB
- **Storage**: 100GB SSD
- **Network**: Stable internet connection

#### Recommended Requirements (Production)
- **OS**: Ubuntu 22.04 LTS
- **CPU**: 8+ cores, 3.0GHz+
- **RAM**: 32GB+
- **Storage**: 500GB+ NVMe SSD
- **Network**: Low-latency, high-bandwidth connection
- **Redundancy**: Multiple availability zones

#### Software Prerequisites
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget build-essential python3.11 python3.11-venv
sudo apt install -y nodejs npm redis-server postgresql postgresql-contrib
sudo apt install -y nginx docker.io docker-compose-plugin

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
```

### Environment Variables

Create environment-specific `.env` files:

#### Backend Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql://niraj:secure_password@localhost:5432/niraj_prod
REDIS_URL=redis://localhost:6379/0

# API Keys (Production - use secrets management)
ANGEL_ONE_API_KEY=your_production_api_key
ANGEL_ONE_SECRET_KEY=your_production_secret_key
DHAN_CLIENT_ID=your_production_client_id
DHAN_ACCESS_TOKEN=your_production_access_token
NEWS_API_KEY=your_news_api_key
WEATHER_API_KEY=your_weather_api_key

# AI Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b-it-q4_K_M
OLLAMA_TEMPERATURE=0.1

# Security
JWT_SECRET_KEY=your_super_secure_256_bit_secret_key_here
PIN_CODE=1937
ENCRYPTION_KEY=your_aes_256_encryption_key

# Application Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
WORKERS=4
RELOAD=false

# Monitoring
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
METRICS_ENABLED=true
PROMETHEUS_PORT=9090

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=1000
RATE_LIMIT_BURST=2000

# CORS and Security
CORS_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]
TRUSTED_HOSTS=["yourdomain.com", "www.yourdomain.com"]
SECURE_COOKIES=true
```

#### Frontend Environment Variables
```bash
# API Configuration
VITE_API_BASE_URL=https://api.yourdomain.com/api/v1
VITE_WS_URL=wss://api.yourdomain.com/ws

# Environment
VITE_ENVIRONMENT=production
VITE_DEBUG=false

# Features
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_ERROR_TRACKING=true

# Security
VITE_CSP_ENABLED=true
```

---

## Development Deployment

### Quick Start (Automated)
```bash
# Clone repository
git clone https://github.com/Pusparaj99op/NIRAJ.git
cd NIRAJ

# Make scripts executable
chmod +x scripts/*.sh

# Run complete setup
./scripts/setup_dev.sh

# Start development servers
./scripts/run_dev.sh
```

### Manual Development Setup

#### Backend Setup
```bash
cd backend/

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
poetry install

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Initialize database
poetry run python -c "from src.core.database_manager import DatabaseManager; import asyncio; asyncio.run(DatabaseManager().initialize())"

# Run database migrations
poetry run alembic upgrade head

# Start development server
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
cd frontend/

# Install dependencies
npm install

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Start development server
npm run dev
```

#### AI Setup
```bash
# Start Ollama service
ollama serve &

# Pull Gemma3 model
ollama pull gemma3:4b-it-q4_K_M

# Verify model availability
ollama list
```

#### Services Setup
```bash
# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Start PostgreSQL (if using)
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database
sudo -u postgres createdb niraj_dev
sudo -u postgres createuser niraj
sudo -u postgres psql -c "ALTER USER niraj PASSWORD 'password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE niraj_dev TO niraj;"
```

---

## Staging Deployment

### Infrastructure Setup
```bash
# Server preparation
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-plugin nginx certbot python3-certbot-nginx

# User setup
sudo usermod -aG docker $USER
newgrp docker

# Firewall configuration
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw --force enable
```

### Docker Compose Deployment
```yaml
# docker-compose.staging.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: niraj_staging
      POSTGRES_USER: niraj
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U niraj"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.staging
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://niraj:${POSTGRES_PASSWORD}@postgres:5432/niraj_staging
      - REDIS_URL=redis://redis:6379/0
      - OLLAMA_BASE_URL=http://ollama:11434
      - ENVIRONMENT=staging
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      ollama:
        condition: service_healthy
    volumes:
      - ./backend/logs:/app/logs
      - ./backend/data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.staging
    ports:
      - "3005:3005"
    environment:
      - VITE_API_BASE_URL=https://staging-api.yourdomain.com/api/v1
      - VITE_WS_URL=wss://staging-api.yourdomain.com/ws
      - VITE_ENVIRONMENT=staging
    depends_on:
      backend:
        condition: service_healthy

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/staging.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
      - nginx_logs:/var/log/nginx
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
  redis_data:
  ollama_data:
  nginx_logs:
```

### Deployment Script
```bash
#!/bin/bash
# deploy-staging.sh

set -e

echo "🚀 Deploying NIRAJ to Staging Environment"

# Pull latest code
git pull origin staging

# Build and start services
docker-compose -f docker-compose.staging.yml down
docker-compose -f docker-compose.staging.yml build --no-cache
docker-compose -f docker-compose.staging.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 30

# Run database migrations
docker-compose -f docker-compose.staging.yml exec backend poetry run alembic upgrade head

# Load Ollama model
docker-compose -f docker-compose.staging.yml exec ollama ollama pull gemma3:4b-it-q4_K_M

# Run health checks
docker-compose -f docker-compose.staging.yml exec backend curl -f http://localhost:8000/health
docker-compose -f docker-compose.staging.yml exec frontend curl -f http://localhost:3005

echo "✅ Staging deployment completed successfully!"
```

---

## Production Deployment

### Infrastructure Requirements

#### Load Balancer Configuration (HAProxy)
```bash
# /etc/haproxy/haproxy.cfg
global
    daemon
    maxconn 4096
    log stdout local0
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy

defaults
    mode http
    timeout connect 5s
    timeout client 50s
    timeout server 50s
    option httplog
    option dontlognull
    option redispatch
    retries 3

frontend niraj_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/niraj.pem
    redirect scheme https if !{ ssl_fc }

    # Security headers
    http-response set-header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    http-response set-header X-Frame-Options "DENY"
    http-response set-header X-Content-Type-Options "nosniff"
    http-response set-header X-XSS-Protection "1; mode=block"

    # Route to backends
    acl is_api path_beg /api/
    acl is_ws path_beg /ws
    use_backend niraj_api if is_api or is_ws
    default_backend niraj_frontend

backend niraj_api
    balance roundrobin
    option httpchk GET /health
    server api1 10.0.1.10:8000 check
    server api2 10.0.1.11:8000 check
    server api3 10.0.1.12:8000 check

backend niraj_frontend
    balance roundrobin
    option httpchk GET /
    server web1 10.0.1.20:3005 check
    server web2 10.0.1.21:3005 check

listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 30s
    stats admin if TRUE
```

#### PostgreSQL High Availability
```bash
# Master-Slave replication setup
# Master server configuration (/etc/postgresql/15/main/postgresql.conf)
listen_addresses = '*'
wal_level = replica
max_wal_senders = 3
max_replication_slots = 3
hot_standby = on

# Slave server configuration
standby_mode = 'on'
primary_conninfo = 'host=master-ip port=5432 user=replicator'
trigger_file = '/tmp/postgresql.trigger'
```

#### Redis Cluster Setup
```bash
# Redis cluster configuration
redis-cli --cluster create \
  10.0.1.30:7000 10.0.1.31:7000 10.0.1.32:7000 \
  10.0.1.30:7001 10.0.1.31:7001 10.0.1.32:7001 \
  --cluster-replicas 1
```

### Kubernetes Deployment

#### Namespace and ConfigMap
```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: niraj-prod

---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: niraj-config
  namespace: niraj-prod
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  REDIS_URL: "redis://redis-service:6379/0"
  OLLAMA_BASE_URL: "http://ollama-service:11434"
```

#### PostgreSQL Deployment
```yaml
# postgres-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: niraj-prod
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        env:
        - name: POSTGRES_DB
          value: "niraj_prod"
        - name: POSTGRES_USER
          value: "niraj"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: niraj-prod
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

#### Redis Deployment
```yaml
# redis-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: niraj-prod
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: niraj-prod
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

#### Backend Deployment
```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: niraj-backend
  namespace: niraj-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: niraj-backend
  template:
    metadata:
      labels:
        app: niraj-backend
    spec:
      containers:
      - name: backend
        image: niraj/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        envFrom:
        - configMapRef:
            name: niraj-config
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: niraj-prod
spec:
  selector:
    app: niraj-backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

#### Ingress Configuration
```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: niraj-ingress
  namespace: niraj-prod
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/use-regex: "true"
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    - app.yourdomain.com
    secretName: niraj-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8000
  - host: app.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 3005
```

### Production Deployment Script
```bash
#!/bin/bash
# deploy-production.sh

set -e

echo "🚀 Deploying NIRAJ to Production Environment"

# Backup current deployment
kubectl create backup production-backup-$(date +%Y%m%d-%H%M%S) || true

# Apply Kubernetes configurations
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/persistent-volumes.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/ollama-deployment.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n niraj-prod --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n niraj-prod --timeout=300s

# Deploy application
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml

# Wait for application to be ready
kubectl wait --for=condition=ready pod -l app=niraj-backend -n niraj-prod --timeout=300s
kubectl wait --for=condition=ready pod -l app=niraj-frontend -n niraj-prod --timeout=300s

# Run database migrations
kubectl exec -n niraj-prod deployment/niraj-backend -- poetry run alembic upgrade head

# Health check
kubectl exec -n niraj-prod deployment/niraj-backend -- curl -f http://localhost:8000/health

echo "✅ Production deployment completed successfully!"
```

---

## Database Management

### Database Setup and Migrations

#### Initial Setup
```bash
# Create database
createdb niraj_prod
createuser niraj
psql -c "ALTER USER niraj PASSWORD 'secure_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE niraj_prod TO niraj;"

# Initialize Alembic
cd backend/
poetry run alembic init alembic
```

#### Migration Management
```bash
# Create new migration
poetry run alembic revision --autogenerate -m "Add new table"

# Apply migrations
poetry run alembic upgrade head

# Rollback migration
poetry run alembic downgrade -1

# Show migration history
poetry run alembic history

# Check current revision
poetry run alembic current
```

#### Database Backup and Restore
```bash
#!/bin/bash
# backup-database.sh

BACKUP_DIR="/var/backups/niraj"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="niraj_backup_$TIMESTAMP.sql"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create backup
pg_dump -h localhost -U niraj -d niraj_prod > "$BACKUP_DIR/$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_DIR/$BACKUP_FILE"

# Remove backups older than 30 days
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Database backup completed: $BACKUP_FILE.gz"
```

```bash
#!/bin/bash
# restore-database.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Stop application
systemctl stop niraj-backend

# Drop and recreate database
dropdb niraj_prod
createdb niraj_prod

# Restore backup
if [[ $BACKUP_FILE == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | psql -h localhost -U niraj -d niraj_prod
else
    psql -h localhost -U niraj -d niraj_prod < "$BACKUP_FILE"
fi

# Start application
systemctl start niraj-backend

echo "Database restored successfully"
```

### Database Optimization

#### Performance Tuning
```sql
-- postgresql.conf optimizations
shared_buffers = 256MB                # 25% of total RAM
effective_cache_size = 1GB           # 75% of total RAM
work_mem = 64MB                      # Per connection
maintenance_work_mem = 256MB         # For maintenance operations
wal_buffers = 16MB                   # Write-ahead log buffers
checkpoint_segments = 32             # Checkpoint frequency
checkpoint_completion_target = 0.7   # Checkpoint completion target

-- Create indexes for performance
CREATE INDEX CONCURRENTLY idx_trades_created_at ON trades(created_at);
CREATE INDEX CONCURRENTLY idx_trades_symbol ON trades(symbol);
CREATE INDEX CONCURRENTLY idx_trades_strategy_id ON trades(strategy_id);
CREATE INDEX CONCURRENTLY idx_market_data_symbol_timestamp ON market_data(symbol, timestamp);
CREATE INDEX CONCURRENTLY idx_ai_predictions_created_at ON ai_predictions(created_at);
```

#### Database Monitoring
```sql
-- Monitor active connections
SELECT count(*) as active_connections
FROM pg_stat_activity
WHERE state = 'active';

-- Monitor slow queries
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Monitor table sizes
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Monitoring & Alerting

### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "niraj_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'niraj-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'niraj-postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'niraj-redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

### Grafana Dashboards

#### System Metrics Dashboard
```json
{
  "dashboard": {
    "title": "NIRAJ System Metrics",
    "panels": [
      {
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Active Trading Strategies",
        "type": "stat",
        "targets": [
          {
            "expr": "niraj_active_strategies_total",
            "legendFormat": "Active Strategies"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends{datname=\"niraj_prod\"}",
            "legendFormat": "Active Connections"
          }
        ]
      }
    ]
  }
}
```

### Alerting Rules
```yaml
# niraj_rules.yml
groups:
- name: niraj_alerts
  rules:
  - alert: HighAPILatency
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High API latency detected"
      description: "95th percentile latency is {{ $value }}s"

  - alert: DatabaseConnectionsHigh
    expr: pg_stat_database_numbackends{datname="niraj_prod"} > 80
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "High database connection count"
      description: "Database has {{ $value }} active connections"

  - alert: TradingStrategyFailure
    expr: increase(niraj_strategy_failures_total[5m]) > 5
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Multiple trading strategy failures"
      description: "{{ $value }} strategy failures in the last 5 minutes"

  - alert: AIModelAccuracyLow
    expr: niraj_ai_model_accuracy < 0.6
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "AI model accuracy below threshold"
      description: "AI model accuracy is {{ $value }}"
```

### Log Aggregation (ELK Stack)

#### Logstash Configuration
```ruby
# logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][service] == "niraj-backend" {
    json {
      source => "message"
    }

    date {
      match => [ "timestamp", "ISO8601" ]
    }

    if [level] == "ERROR" {
      mutate {
        add_tag => [ "error" ]
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "niraj-logs-%{+YYYY.MM.dd}"
  }
}
```

#### Elasticsearch Index Template
```json
{
  "index_patterns": ["niraj-logs-*"],
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1,
    "index.refresh_interval": "30s"
  },
  "mappings": {
    "properties": {
      "@timestamp": {"type": "date"},
      "level": {"type": "keyword"},
      "message": {"type": "text"},
      "service": {"type": "keyword"},
      "trade_id": {"type": "keyword"},
      "strategy": {"type": "keyword"},
      "user_id": {"type": "keyword"}
    }
  }
}
```

---

## Backup & Recovery

### Automated Backup Strategy

#### Complete Backup Script
```bash
#!/bin/bash
# full-backup.sh

set -e

BACKUP_DIR="/var/backups/niraj"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

echo "Starting NIRAJ full backup - $TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_DIR/$TIMESTAMP"

# Database backup
echo "Backing up database..."
pg_dump -h localhost -U niraj -d niraj_prod | gzip > "$BACKUP_DIR/$TIMESTAMP/database.sql.gz"

# Redis backup
echo "Backing up Redis..."
redis-cli --rdb "$BACKUP_DIR/$TIMESTAMP/redis.rdb"
gzip "$BACKUP_DIR/$TIMESTAMP/redis.rdb"

# Application data backup
echo "Backing up application data..."
tar -czf "$BACKUP_DIR/$TIMESTAMP/app_data.tar.gz" /var/lib/niraj/data

# Configuration backup
echo "Backing up configurations..."
tar -czf "$BACKUP_DIR/$TIMESTAMP/configs.tar.gz" /etc/niraj /var/lib/niraj/config

# Log backup
echo "Backing up logs..."
tar -czf "$BACKUP_DIR/$TIMESTAMP/logs.tar.gz" /var/log/niraj

# Create backup manifest
cat > "$BACKUP_DIR/$TIMESTAMP/manifest.txt" << EOF
NIRAJ Backup Manifest
Created: $TIMESTAMP
Database: database.sql.gz
Cache: redis.rdb.gz
App Data: app_data.tar.gz
Configs: configs.tar.gz
Logs: logs.tar.gz
EOF

# Upload to cloud storage (AWS S3 example)
if command -v aws &> /dev/null; then
    echo "Uploading to S3..."
    aws s3 sync "$BACKUP_DIR/$TIMESTAMP" "s3://niraj-backups/$TIMESTAMP"
fi

# Clean up old backups
find "$BACKUP_DIR" -maxdepth 1 -type d -mtime +$RETENTION_DAYS -exec rm -rf {} \;

echo "Backup completed successfully - $TIMESTAMP"
```

### Disaster Recovery Procedures

#### Recovery Checklist
1. **Assess Damage**: Determine scope of failure
2. **Isolate Systems**: Prevent further damage
3. **Activate DR Site**: Switch to backup infrastructure
4. **Restore Data**: Apply latest backups
5. **Verify Integrity**: Run data validation checks
6. **Resume Operations**: Gradually restore trading
7. **Post-Incident**: Document and improve procedures

#### Recovery Script
```bash
#!/bin/bash
# disaster-recovery.sh

BACKUP_TIMESTAMP=$1
BACKUP_DIR="/var/backups/niraj"

if [ -z "$BACKUP_TIMESTAMP" ]; then
    echo "Usage: $0 <backup_timestamp>"
    echo "Available backups:"
    ls -la "$BACKUP_DIR"
    exit 1
fi

RESTORE_PATH="$BACKUP_DIR/$BACKUP_TIMESTAMP"

if [ ! -d "$RESTORE_PATH" ]; then
    echo "Backup not found: $RESTORE_PATH"
    exit 1
fi

echo "🚨 Starting disaster recovery from backup: $BACKUP_TIMESTAMP"

# Stop all services
echo "Stopping services..."
systemctl stop niraj-backend
systemctl stop niraj-frontend
systemctl stop niraj-websocket

# Restore database
echo "Restoring database..."
dropdb niraj_prod || true
createdb niraj_prod
gunzip -c "$RESTORE_PATH/database.sql.gz" | psql -U niraj -d niraj_prod

# Restore Redis
echo "Restoring Redis..."
systemctl stop redis-server
gunzip -c "$RESTORE_PATH/redis.rdb.gz" > /var/lib/redis/dump.rdb
chown redis:redis /var/lib/redis/dump.rdb
systemctl start redis-server

# Restore application data
echo "Restoring application data..."
tar -xzf "$RESTORE_PATH/app_data.tar.gz" -C /

# Restore configurations
echo "Restoring configurations..."
tar -xzf "$RESTORE_PATH/configs.tar.gz" -C /

# Start services
echo "Starting services..."
systemctl start redis-server
systemctl start postgresql
sleep 10
systemctl start niraj-backend
systemctl start niraj-frontend
systemctl start niraj-websocket

# Health checks
echo "Running health checks..."
sleep 30
curl -f http://localhost:8000/health || echo "Backend health check failed"
curl -f http://localhost:3005 || echo "Frontend health check failed"

echo "✅ Disaster recovery completed"
echo "⚠️  Please verify system integrity before resuming trading"
```

---

## Security Hardening

### System Security

#### Firewall Configuration
```bash
# Configure UFW firewall
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (change port from default)
sudo ufw allow 2222/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow internal communication
sudo ufw allow from 10.0.0.0/8 to any port 5432  # PostgreSQL
sudo ufw allow from 10.0.0.0/8 to any port 6379  # Redis
sudo ufw allow from 10.0.0.0/8 to any port 8000  # Backend API

# Enable firewall
sudo ufw --force enable

# Rate limiting for SSH
sudo ufw limit ssh
```

#### SSH Hardening
```bash
# /etc/ssh/sshd_config
Port 2222
Protocol 2
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
X11Forwarding no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
AllowUsers niraj
```

#### Fail2ban Configuration
```bash
# /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = 2222

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
```

### Application Security

#### Security Headers (Nginx)
```nginx
# /etc/nginx/sites-available/niraj
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' wss:; font-src 'self';" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Database Security
```sql
-- Create restricted database users
CREATE USER niraj_readonly WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE niraj_prod TO niraj_readonly;
GRANT USAGE ON SCHEMA public TO niraj_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO niraj_readonly;

-- Enable row-level security
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_trades ON trades FOR ALL TO niraj USING (user_id = current_setting('app.current_user_id')::integer);

-- Audit logging
CREATE EXTENSION IF NOT EXISTS pgaudit;
```

### Secrets Management

#### HashiCorp Vault Integration
```bash
# Install Vault
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt update && sudo apt install vault

# Configure Vault
vault server -config=/etc/vault/vault.hcl

# Store secrets
vault kv put secret/niraj/database url="postgresql://..." password="..."
vault kv put secret/niraj/api angel_one_key="..." dhan_token="..."
```

#### Kubernetes Secrets
```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: niraj-secrets
  namespace: niraj-prod
type: Opaque
data:
  database-url: <base64-encoded-database-url>
  jwt-secret: <base64-encoded-jwt-secret>
  angel-one-key: <base64-encoded-api-key>
```

---

## Performance Tuning

### Application Optimization

#### FastAPI Optimization
```python
# main.py optimizations
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()

# Enable compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Connection pooling
from sqlalchemy.pool import QueuePool
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=300
)

# Redis connection pooling
redis_pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    db=0,
    max_connections=100
)
```

#### Database Optimization
```sql
-- Optimize PostgreSQL settings
-- postgresql.conf
shared_buffers = 1GB                    # 25% of RAM
effective_cache_size = 3GB              # 75% of RAM
maintenance_work_mem = 256MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1                  # For SSD
effective_io_concurrency = 200          # For SSD

-- Create optimal indexes
CREATE INDEX CONCURRENTLY idx_trades_user_created ON trades(user_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_market_data_symbol_time ON market_data(symbol) INCLUDE(timestamp, close);
CREATE INDEX CONCURRENTLY idx_strategies_active ON strategies(is_active) WHERE is_active = true;

-- Partitioning for large tables
CREATE TABLE market_data_2024 PARTITION OF market_data
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

#### Redis Optimization
```bash
# redis.conf optimizations
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
tcp-keepalive 300
timeout 0
```

### System Optimization

#### Kernel Parameters
```bash
# /etc/sysctl.conf
# Network optimization
net.core.rmem_default = 262144
net.core.rmem_max = 16777216
net.core.wmem_default = 262144
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 262144 16777216
net.ipv4.tcp_wmem = 4096 262144 16777216

# File system optimization
fs.file-max = 65536
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
```

#### Container Resource Limits
```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
```

---

## Troubleshooting

### Common Issues and Solutions

#### High API Latency
```bash
# Check system resources
htop
iostat -x 1
netstat -i

# Check database performance
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;

# Check Redis performance
redis-cli --latency-history -i 1

# Application logs
docker logs niraj-backend --tail=100 -f
```

#### Database Connection Issues
```bash
# Check connection count
SELECT count(*) FROM pg_stat_activity;

# Kill idle connections
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '1 hour';

# Check connection pool
# In application logs, look for:
# "ConnectionPoolLimit exceeded"
# "Connection timeout"
```

#### WebSocket Connection Problems
```bash
# Check WebSocket connections
netstat -an | grep :8000 | grep ESTABLISHED | wc -l

# Check for connection limits
ulimit -n

# Increase file descriptor limits
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf
```

#### AI Model Issues
```bash
# Check Ollama service
systemctl status ollama
ollama list
ollama ps

# Check model loading
curl http://localhost:11434/api/generate -d '{"model":"gemma3:4b-it-q4_K_M","prompt":"test"}'

# Check GPU usage (if applicable)
nvidia-smi
```

### Log Analysis

#### Application Logs
```bash
# Real-time log monitoring
tail -f /var/log/niraj/app.log | jq '.'

# Error analysis
grep "ERROR" /var/log/niraj/app.log | jq -r '.message' | sort | uniq -c | sort -nr

# Performance analysis
grep "duration" /var/log/niraj/app.log | jq -r '.duration' | awk '{sum+=$1; count++} END {print "Average:", sum/count}'
```

#### System Logs
```bash
# System errors
journalctl -f -u niraj-backend

# Database logs
tail -f /var/log/postgresql/postgresql-15-main.log

# Nginx logs
tail -f /var/log/nginx/access.log | awk '{print $7}' | sort | uniq -c | sort -nr
```

### Performance Debugging

#### Database Query Analysis
```sql
-- Slow query analysis
SELECT query, calls, total_time, mean_time, rows
FROM pg_stat_statements
WHERE mean_time > 100
ORDER BY mean_time DESC;

-- Lock analysis
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

#### Memory Analysis
```bash
# Python memory profiling
pip install memory-profiler
python -m memory_profiler your_script.py

# Check for memory leaks
ps aux --sort=-%mem | head -10

# System memory usage
free -m
cat /proc/meminfo
```

---

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily Tasks
```bash
#!/bin/bash
# daily-maintenance.sh

# Check system health
curl -f http://localhost:8000/health || echo "Backend health check failed"

# Check disk space
df -h | awk '$5 > 80 {print "WARNING: " $0}'

# Backup database
/scripts/backup-database.sh

# Rotate logs
logrotate /etc/logrotate.d/niraj

# Check for failed services
systemctl --failed
```

#### Weekly Tasks
```bash
#!/bin/bash
# weekly-maintenance.sh

# Update system packages
apt update && apt list --upgradable

# Analyze database performance
psql -U niraj -d niraj_prod -c "SELECT schemaname,tablename,attname,n_distinct,correlation FROM pg_stats WHERE schemaname='public' ORDER BY n_distinct DESC;"

# Clean up old files
find /var/log/niraj -name "*.log" -mtime +30 -delete
find /tmp -name "niraj_*" -mtime +7 -delete

# Check SSL certificate expiry
openssl x509 -in /etc/ssl/certs/niraj.pem -text -noout | grep "Not After"
```

#### Monthly Tasks
```bash
#!/bin/bash
# monthly-maintenance.sh

# Full system backup
/scripts/full-backup.sh

# Database maintenance
psql -U niraj -d niraj_prod -c "VACUUM ANALYZE;"
psql -U niraj -d niraj_prod -c "REINDEX DATABASE niraj_prod;"

# Security updates
apt update && apt upgrade -y

# Certificate renewal
certbot renew --nginx

# Performance review
/scripts/generate-performance-report.sh
```

### Update Procedures

#### Application Updates
```bash
#!/bin/bash
# update-application.sh

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

echo "Updating NIRAJ to version $VERSION"

# Backup before update
/scripts/full-backup.sh

# Pull new version
git fetch origin
git checkout "v$VERSION"

# Update dependencies
cd backend && poetry install
cd ../frontend && npm install

# Run database migrations
cd backend && poetry run alembic upgrade head

# Build and restart services
docker-compose build
docker-compose up -d

# Health check
sleep 30
curl -f http://localhost:8000/health

echo "Update completed successfully"
```

#### Security Updates
```bash
#!/bin/bash
# security-updates.sh

# System security updates
apt update
apt upgrade -y

# Update Python dependencies
cd backend
poetry update
poetry audit

# Update Node.js dependencies
cd ../frontend
npm audit fix
npm update

# Update Docker images
docker-compose pull
docker-compose up -d

# Restart services
systemctl restart niraj-backend
systemctl restart niraj-frontend

echo "Security updates completed"
```

### Monitoring and Alerting Setup

#### Monitoring Script
```bash
#!/bin/bash
# monitor-system.sh

ALERT_EMAIL="admin@yourdomain.com"
THRESHOLD_CPU=80
THRESHOLD_MEMORY=80
THRESHOLD_DISK=90

# Check CPU usage
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
if (( $(echo "$CPU_USAGE > $THRESHOLD_CPU" | bc -l) )); then
    echo "High CPU usage: $CPU_USAGE%" | mail -s "NIRAJ Alert: High CPU" $ALERT_EMAIL
fi

# Check memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')
if (( $(echo "$MEMORY_USAGE > $THRESHOLD_MEMORY" | bc -l) )); then
    echo "High memory usage: $MEMORY_USAGE%" | mail -s "NIRAJ Alert: High Memory" $ALERT_EMAIL
fi

# Check disk usage
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)
if [ $DISK_USAGE -gt $THRESHOLD_DISK ]; then
    echo "High disk usage: $DISK_USAGE%" | mail -s "NIRAJ Alert: High Disk Usage" $ALERT_EMAIL
fi

# Check service status
for service in niraj-backend niraj-frontend postgresql redis-server; do
    if ! systemctl is-active --quiet $service; then
        echo "Service $service is not running" | mail -s "NIRAJ Alert: Service Down" $ALERT_EMAIL
    fi
done
```

This comprehensive deployment and operations guide provides everything needed to successfully deploy, monitor, and maintain the NIRAJ trading system in production environments. Regular execution of these procedures ensures optimal performance, security, and reliability.
