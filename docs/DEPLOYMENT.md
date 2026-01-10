# Deployment Guide - ArXiv Co-Scientist

Complete guide for deploying the ArXiv Co-Scientist application to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Local Development](#local-development)
4. [Production Deployment](#production-deployment)
5. [Docker Deployment](#docker-deployment)
6. [Kubernetes Deployment](#kubernetes-deployment)
7. [Monitoring & Observability](#monitoring--observability)
8. [Backup & Recovery](#backup--recovery)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum:**
- 4 CPU cores
- 8GB RAM
- 50GB disk space
- Docker 24.0+ & Docker Compose 2.20+

**Recommended (Production):**
- 8+ CPU cores
- 16GB+ RAM
- 200GB+ SSD storage
- Kubernetes 1.28+ (for K8s deployment)

### Required Services

- **Neo4j Community 5.15+** - Graph database
- **ChromaDB** - Vector database (embedded)
- **Grobid 0.8.0** - PDF parsing service

### API Keys (Free Tier)

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional (improved rate limits)
S2_API_KEY=your_semantic_scholar_key  # 10 req/sec vs 1 req/sec
GROQ_API_KEY=your_groq_key            # Fallback LLM provider
```

---

## Environment Configuration

### 1. Create Environment File

```bash
# Copy example environment file
cp .env.example .env.prod

# Edit with your values
nano .env.prod
```

### 2. Production Environment Variables

```bash
# .env.prod
# ==================
# Service Configuration
# ==================
ENVIRONMENT=production
LOG_LEVEL=INFO
LOG_FORMAT=json

# ==================
# Database Configuration
# ==================
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password_here  # CHANGE THIS!

# ==================
# API Keys
# ==================
GEMINI_API_KEY=your_gemini_key
S2_API_KEY=your_s2_key
GROQ_API_KEY=your_groq_key

# ==================
# LLM Configuration
# ==================
LLM_PROVIDER=gemini  # or groq, ollama

# ==================
# Service URLs
# ==================
GROBID_URL=http://grobid:8070
API_URL=http://api:8000

# ==================
# Security
# ==================
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 3. Security Checklist

- [ ] Change default Neo4j password
- [ ] Set strong passwords (min 16 chars, mixed case, numbers, symbols)
- [ ] Restrict CORS origins to your domain
- [ ] Use HTTPS in production (setup SSL certificates)
- [ ] Never commit `.env.prod` to version control
- [ ] Rotate API keys quarterly
- [ ] Enable firewall rules (only expose necessary ports)

---

## Local Development

### Quick Start

```bash
# 1. Install dependencies
poetry install

# 2. Start databases
docker compose up -d neo4j grobid

# 3. Initialize database schema
poetry run arxiv-cosci init-db

# 4. Run API server (development mode)
poetry run uvicorn apps.api.main:app --reload --port 8000

# 5. Run frontend (in separate terminal)
cd apps/web
npm install
npm run dev
```

### Development with Docker

```bash
# Build and run all services
docker compose up --build

# Access services:
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Neo4j Browser: http://localhost:7474
# - Frontend: http://localhost:5173
```

---

## Production Deployment

### Option 1: Docker Compose (Recommended for Single Server)

#### Step 1: Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install docker-compose-plugin
```

#### Step 2: Clone Repository

```bash
# Clone project
git clone https://github.com/yourusername/arxiv-cosci.git
cd arxiv-cosci

# Checkout production branch
git checkout main
```

#### Step 3: Configure Environment

```bash
# Create production environment file
cp .env.example .env.prod

# Edit with production values
nano .env.prod

# Set file permissions (restrict access)
chmod 600 .env.prod
```

#### Step 4: Deploy Services

```bash
# Build and start production services
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Check service health
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

#### Step 5: Initialize Database

```bash
# Initialize Neo4j schema
docker compose -f docker-compose.prod.yml exec api \
  poetry run arxiv-cosci init-db
```

#### Step 6: Verify Deployment

```bash
# Test API health
curl http://localhost:8000/api/health
curl http://localhost:8000/api/health/db

# Test metrics endpoint
curl http://localhost:8000/metrics

# View logs
docker compose -f docker-compose.prod.yml logs -f api
```

### Option 2: Manual Installation

#### Install Python Application

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install --no-dev

# Run with gunicorn (production WSGI server)
poetry run gunicorn apps.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

#### Setup Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/arxiv-api.service
```

```ini
[Unit]
Description=ArXiv Co-Scientist API
After=network.target neo4j.service

[Service]
Type=notify
User=arxiv
Group=arxiv
WorkingDirectory=/opt/arxiv-cosci
Environment="PATH=/opt/arxiv-cosci/.venv/bin"
EnvironmentFile=/opt/arxiv-cosci/.env.prod
ExecStart=/opt/arxiv-cosci/.venv/bin/gunicorn apps.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable arxiv-api
sudo systemctl start arxiv-api
sudo systemctl status arxiv-api
```

---

## Kubernetes Deployment

### Prerequisites

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### Deploy to Kubernetes

#### 1. Create Namespace

```bash
kubectl create namespace arxiv-cosci
```

#### 2. Create Secrets

```bash
# Create secret for API keys
kubectl create secret generic arxiv-secrets \
  --from-literal=neo4j-password=your_password \
  --from-literal=gemini-api-key=your_key \
  --from-literal=s2-api-key=your_key \
  -n arxiv-cosci
```

#### 3. Deploy Neo4j (using Helm)

```bash
# Add Neo4j Helm repository
helm repo add neo4j https://helm.neo4j.com/neo4j
helm repo update

# Install Neo4j
helm install arxiv-neo4j neo4j/neo4j \
  --namespace arxiv-cosci \
  --set neo4j.password=your_password \
  --set volumes.data.mode=defaultStorageClass \
  --set volumes.data.defaultStorageClass.requests.storage=10Gi
```

#### 4. Deploy API Service

```yaml
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
meta
  name: arxiv-api
  namespace: arxiv-cosci
spec:
  replicas: 3
  selector:
    matchLabels:
      app: arxiv-api
  template:
    meta
      labels:
        app: arxiv-api
    spec:
      containers:
      - name: api
        image: your-registry/arxiv-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: NEO4J_URI
          value: "bolt://arxiv-neo4j:7687"
        - name: NEO4J_PASSWORD
          valueFrom:
            secretKeyRef:
              name: arxiv-secrets
              key: neo4j-password
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: arxiv-secrets
              key: gemini-api-key
        livenessProbe:
          httpGet:
            path: /api/health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
---
apiVersion: v1
kind: Service
meta
  name: arxiv-api
  namespace: arxiv-cosci
spec:
  selector:
    app: arxiv-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

```bash
# Apply deployment
kubectl apply -f k8s/api-deployment.yaml

# Check deployment status
kubectl get pods -n arxiv-cosci
kubectl logs -f deployment/arxiv-api -n arxiv-cosci
```

---

## Monitoring & Observability

### Health Check Endpoints

```bash
# Liveness probe (is service alive?)
curl http://localhost:8000/api/health/live

# Readiness probe (is service ready to accept traffic?)
curl http://localhost:8000/api/health/ready

# Database health
curl http://localhost:8000/api/health/db

# Performance metrics
curl http://localhost:8000/metrics
```

### Structured Logging

Logs are output in JSON format in production:

```json
{
  "event": "Request completed",
  "level": "info",
  "timestamp": "2026-01-10T22:30:00.000Z",
  "request_id": "abc-123",
  "method": "GET",
  "path": "/api/papers/2401.12345",
  "status_code": 200,
  "duration_ms": 45.2,
  "app": "arxiv-cosci",
  "version": "0.4.0"
}
```

### Log Aggregation

#### Option 1: ELK Stack

```bash
# Forward logs to Elasticsearch
docker compose -f docker-compose.prod.yml logs -f api | \
  logstash -f logstash.conf
```

#### Option 2: Cloud Logging

```bash
# Google Cloud Logging
gcloud logging write arxiv-api "Log message" --severity=INFO

# AWS CloudWatch
aws logs put-log-events \
  --log-group-name /arxiv-cosci/api \
  --log-stream-name production
```

### Metrics Collection

The `/metrics` endpoint provides:
- Request counts by endpoint
- Response time percentiles (p50, p95, p99)
- Error rates
- Database query performance
- System uptime

Example Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: 'arxiv-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

---

## Backup & Recovery

### Neo4j Backup

```bash
# Manual backup
docker compose exec neo4j neo4j-admin database dump neo4j \
  --to-path=/backups/neo4j-$(date +%Y%m%d).dump

# Automated daily backup (cron)
0 2 * * * docker compose exec neo4j neo4j-admin database dump neo4j \
  --to-path=/backups/neo4j-$(date +%Y%m%d).dump
```

### Neo4j Restore

```bash
# Stop Neo4j
docker compose stop neo4j

# Restore from backup
docker compose exec neo4j neo4j-admin database load neo4j \
  --from-path=/backups/neo4j-20260110.dump --overwrite-destination=true

# Start Neo4j
docker compose start neo4j
```

### Data Volume Backup

```bash
# Backup Docker volumes
docker run --rm \
  -v arxiv-cosci_neo4j_/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/neo4j-data-$(date +%Y%m%d).tar.gz /data
```

---

## Troubleshooting

### Common Issues

#### 1. API Won't Start

```bash
# Check logs
docker compose logs api

# Verify environment variables
docker compose exec api env | grep NEO4J

# Test database connection
docker compose exec api poetry run arxiv-cosci check
```

#### 2. Neo4j Connection Failed

```bash
# Verify Neo4j is running
docker compose ps neo4j

# Check Neo4j logs
docker compose logs neo4j

# Test connection
docker compose exec neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n);"
```

#### 3. Slow API Response

```bash
# Check metrics
curl http://localhost:8000/metrics

# View slow requests in logs
docker compose logs api | grep "Slow request"

# Monitor resource usage
docker stats
```

#### 4. Out of Memory

```bash
# Increase Neo4j heap size
# Edit docker-compose.prod.yml:
NEO4J_server_memory_heap_max__size=4g

# Increase API workers (reduce if OOM)
CMD ["uvicorn", "apps.api.main:app", "--workers", "2"]  # Reduce from 4 to 2

# Monitor memory
docker stats --no-stream
```

### Debug Mode

```bash
# Enable debug logging
docker compose -f docker-compose.prod.yml up -d \
  -e LOG_LEVEL=DEBUG

# View detailed logs
docker compose logs -f --tail=100 api