# CloudCapsule — Cost Estimation Worksheet

No price is asserted here because actual cost depends on region, usage, configuration, and current AWS rates. Populate this worksheet using AWS Pricing Calculator for the selected region (proposed default: Mumbai, `ap-south-1`) before approving deployment.

| Component | Required input for estimate | Notes |
|---|---|---|
| ECS Fargate API | vCPU, memory, desired tasks, hours/month | Include worker tasks separately |
| Application Load Balancer | Hours/month, estimated LCU usage | Recurring cost even at low traffic |
| RDS PostgreSQL | Instance class, Multi-AZ choice, storage, I/O, backup retention | Multi-AZ changes cost materially |
| NAT gateway | Number of gateways, hours, data processed | Often a major fixed cost |
| VPC endpoints | Endpoint types and hours | Compare with NAT for expected traffic |
| S3 | Storage GB, requests, versioning | Include old versions and lifecycle rules |
| CloudFront | Data transfer and requests | Depends on traffic and cache behavior |
| ECR | Image storage GB and transfer | Clean up old image tags under a policy |
| CloudWatch | Logs ingested/stored, metrics, alarms | Set log retention |
| SQS | Requests and payload volume | Usually usage-dependent |
| KMS / Secrets Manager | Keys, API calls, secret count | Include rotation if configured |
| AWS Backup | Protected GB, retention, copies | Include cross-region copies if selected |
| Route 53 / ACM / WAF | Hosted zones, certificates, WAF rules/requests | Some components are optional |

## Approval gate

Before deployment, record:
- Region:
- Expected monthly requests / data transfer:
- API and worker task counts:
- RDS instance and Multi-AZ choice:
- NAT/VPC endpoint choice:
- Backup retention and cross-region copies:
- Estimated monthly total and safety margin:
- Maximum approved monthly spend:

Do not run `terraform apply` until the estimate and architecture are explicitly approved.
