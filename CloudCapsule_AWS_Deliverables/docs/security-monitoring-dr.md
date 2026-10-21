# CloudCapsule — Security, Monitoring, Backup and DR Plan

## Current implementation versus target

| Capability | Current local status | Proposed AWS target |
|---|---|---|
| API | FastAPI in Docker Compose | ECS Fargate |
| Database | PostgreSQL container with named volume | Private RDS PostgreSQL |
| Frontend | Vite development server | S3 private origin + CloudFront |
| Lifecycle | Local simulation with audit events | SQS + worker; implementation still required |
| Secrets | Local `.env` ignored by Git | Secrets Manager + KMS |
| Monitoring | Health endpoints and container logs | CloudWatch dashboards, alarms, logs |
| Backup / DR | No verified cloud backup | RDS backups, S3 versioning, tested restore |
| IaC | Terraform files are a starting design only | Reviewed, version-controlled Terraform |

## Security controls

- Restrict ingress to HTTPS at the public entry point.
- Keep application tasks and database in private subnets.
- Permit PostgreSQL only from the application/worker security group.
- Use least-privilege ECS task and execution roles.
- Encrypt database, object storage, logs, and backups where supported.
- Rotate database credentials through Secrets Manager.
- Scan container images and pin production images to immutable versions/digests.
- Validate all API input and enforce authorization before exposing the API publicly.
- Audit administrative actions and lifecycle requests.
- Keep secrets and Terraform state out of source control.

## Monitoring checklist

- API availability, latency, 4xx/5xx rates.
- ECS task count, restarts, CPU and memory.
- RDS storage, connections, CPU, and failover events.
- SQS visible messages, age of oldest message, and DLQ depth.
- Backup job success and restore-test outcomes.
- Security findings and CloudTrail events.

## Backup and recovery checklist

1. Define data classification and retention requirements.
2. Configure RDS automated backups and approved retention.
3. Enable S3 versioning for frontend assets and any user data bucket.
4. Restrict backup deletion permissions.
5. Document point-in-time recovery and infrastructure recreation.
6. Run a restore drill in a non-production environment.
7. Measure actual RPO/RTO; do not claim objectives are met until verified.

## Cost controls

- Select the AWS region and monthly budget before deployment.
- Use AWS Pricing Calculator with explicit assumptions for task count, vCPU, memory, ALB hours/LCUs, RDS class/storage, NAT, S3, CloudFront, logs, and backups.
- Set AWS Budgets and billing alerts.
- Avoid NAT gateways, Multi-AZ database, WAF, or always-on workers until their cost and availability trade-offs are approved.
- Tear down test resources after testing; retain only explicitly approved data/backups.
