# Kubernetes Deployment for ArXiv Co-Scientist

This directory contains Kubernetes manifests for deploying the ArXiv AI Co-Scientist platform.

## Architecture

```
┌─────────────┐
│   Ingress   │ (TLS termination, routing)
└──────┬──────┘
       │
   ┌───┴────┐
   │        │
┌──▼──┐  ┌─▼──┐
│ Web │  │ API│ (3 replicas)
└─────┘  └──┬─┘
            │
      ┌─────┴─────┐
      │           │
   ┌──▼──┐    ┌──▼────┐
   │Neo4j│    │ChromaDB│
   └─────┘    └───────┘
```

## Prerequisites

1. **Kubernetes Cluster** (1.24+)
   - Local: Minikube, Kind, Docker Desktop
   - Cloud: GKE, EKS, AKS

2. **kubectl** configured and connected

3. **Container Images Built**
   ```bash
   # Build API image
   docker build -f Dockerfile.api -t arxiv-cosci-api:latest .
   
   # Build Web image
   docker build -f apps/web/Dockerfile.prod -t arxiv-cosci-web:latest .
   
   # Push to registry (adjust for your registry)
   docker tag arxiv-cosci-api:latest your-registry/arxiv-cosci-api:latest
   docker push your-registry/arxiv-cosci-api:latest
   
   docker tag arxiv-cosci-web:latest your-registry/arxiv-cosci-web:latest
   docker push your-registry/arxiv-cosci-web:latest
   ```

4. **Storage Class** (for persistent volumes)
   ```bash
   kubectl get storageclass
   ```

5. **Optional: Ingress Controller**
   ```bash
   # For nginx ingress
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml
   ```

6. **Optional: Cert-Manager** (for TLS)
   ```bash
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
   ```

## Deployment Steps

### 1. Create Namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. Set Secrets

Create a file `secrets.env` with your credentials (DO NOT commit this):

```bash
# secrets.env
GEMINI_API_KEY=your_gemini_api_key_here
S2_API_KEY=your_s2_api_key_here
NEO4J_PASSWORD=strong_password_here
```

Apply secrets:

```bash
kubectl create secret generic api-secrets \
  --from-env-file=secrets.env \
  --namespace=arxiv-cosci
```

### 3. Deploy Neo4j

```bash
kubectl apply -f neo4j-statefulset.yaml
```

Wait for Neo4j to be ready:

```bash
kubectl wait --for=condition=ready pod -l app=neo4j -n arxiv-cosci --timeout=300s
```

### 4. Initialize Neo4j Schema

```bash
# Port-forward to Neo4j
kubectl port-forward -n arxiv-cosci svc/neo4j 7687:7687 &

# Run schema initialization (from your local machine)
poetry run arxiv-cosci init-db

# Stop port-forward
kill %1
```

### 5. Deploy API

Update `api-deployment.yaml` to use your container registry, then:

```bash
kubectl apply -f api-deployment.yaml
```

Wait for API to be ready:

```bash
kubectl wait --for=condition=ready pod -l app=api -n arxiv-cosci --timeout=300s
```

### 6. Deploy Web Frontend

Update `web-deployment.yaml` with your domain name and container registry, then:

```bash
kubectl apply -f web-deployment.yaml
```

### 7. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n arxiv-cosci

# Check services
kubectl get svc -n arxiv-cosci

# Check logs
kubectl logs -n arxiv-cosci -l app=api --tail=50
kubectl logs -n arxiv-cosci -l app=web --tail=50
```

### 8. Access the Application

#### With LoadBalancer:

```bash
kubectl get svc web -n arxiv-cosci
# Note the EXTERNAL-IP
```

#### With Port-Forward (development):

```bash
# Forward web
kubectl port-forward -n arxiv-cosci svc/web 8080:80

# Forward API
kubectl port-forward -n arxiv-cosci svc/api 8000:8000

# Access at http://localhost:8080
```

#### With Ingress:

1. Point your domain to the ingress controller IP
2. Access at https://arxiv-cosci.example.com

## Scaling

### Scale API

```bash
kubectl scale deployment api --replicas=5 -n arxiv-cosci
```

### Scale Web

```bash
kubectl scale deployment web --replicas=3 -n arxiv-cosci
```

### Neo4j Scaling

Neo4j Community Edition doesn't support horizontal scaling. For production:
- Upgrade to Neo4j Enterprise for clustering
- Or use a managed service (Neo4j Aura, AWS Neptune)

## Monitoring

### View Logs

```bash
# API logs
kubectl logs -f -n arxiv-cosci -l app=api

# Web logs
kubectl logs -f -n arxiv-cosci -l app=web

# Neo4j logs
kubectl logs -f -n arxiv-cosci -l app=neo4j
```

### Resource Usage

```bash
kubectl top pods -n arxiv-cosci
kubectl top nodes
```

## Troubleshooting

### Pod Not Starting

```bash
kubectl describe pod <pod-name> -n arxiv-cosci
kubectl logs <pod-name> -n arxiv-cosci
```

### API Can't Connect to Neo4j

```bash
# Test connection from API pod
kubectl exec -it -n arxiv-cosci <api-pod-name> -- sh
nc -zv neo4j 7687
```

### Check API Health

```bash
kubectl port-forward -n arxiv-cosci svc/api 8000:8000
curl http://localhost:8000/health
```

## Backup & Restore

### Backup Neo4j

```bash
# Create backup
kubectl exec -n arxiv-cosci neo4j-0 -- neo4j-admin database dump neo4j --to-path=/tmp
kubectl cp arxiv-cosci/neo4j-0:/tmp/neo4j.dump ./neo4j-backup.dump
```

### Restore Neo4j

```bash
kubectl cp ./neo4j-backup.dump arxiv-cosci/neo4j-0:/tmp/neo4j.dump
kubectl exec -n arxiv-cosci neo4j-0 -- neo4j-admin database load neo4j --from-path=/tmp
```

## Cleanup

```bash
# Delete all resources
kubectl delete namespace arxiv-cosci

# Or delete individually
kubectl delete -f web-deployment.yaml
kubectl delete -f api-deployment.yaml
kubectl delete -f neo4j-statefulset.yaml
kubectl delete -f namespace.yaml
```

## Production Considerations

1. **Use a private container registry** (GCR, ECR, ACR, Harbor)
2. **Set resource limits** appropriately based on load testing
3. **Enable RBAC** and service accounts
4. **Use NetworkPolicies** to restrict pod-to-pod traffic
5. **Enable pod security policies**
6. **Set up monitoring** (Prometheus, Grafana)
7. **Configure log aggregation** (ELK, Loki)
8. **Use managed databases** for production (Neo4j Aura, managed PostgreSQL)
9. **Implement GitOps** (ArgoCD, Flux)
10. **Regular backups** automated via CronJob

## Environment-Specific Configs

### Development

- Use NodePort services instead of LoadBalancer
- Reduce resource requests/limits
- Use local storage class
- Single replica deployments

### Staging

- Use LoadBalancer services
- Moderate resources
- Multiple replicas for API (2-3)
- Test TLS certificates

### Production

- Use Ingress with TLS
- High resource limits
- High availability (3+ replicas)
- Monitoring and alerting enabled
- Automated backups
- Disaster recovery plan

## Cost Optimization

1. **Right-size resources** - Monitor and adjust limits
2. **Use spot/preemptible instances** for non-critical workloads
3. **Implement HPA** (Horizontal Pod Autoscaler)
4. **Use node auto-scaling**
5. **Schedule non-urgent jobs** during off-peak hours

## Support

For issues, see:
- Main README.md
- docs/DEPLOYMENT.md
- GitHub Issues

## License

MIT - See LICENSE file