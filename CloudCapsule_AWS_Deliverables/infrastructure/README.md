# Terraform infrastructure starter

This directory is a **configuration starter**, not a deployed environment. It intentionally does not create AWS resources by itself. The included Terraform defines only input variables and local values so the proposed architecture and cost assumptions can be reviewed safely.

Next implementation stages (after cost/architecture approval): add VPC/subnets/security groups, ECR, ALB, ECS, RDS, S3/CloudFront, IAM, SQS, logs/alarms, and backup policies as separate modules. Review the plan and estimated cost before any apply.

Do not commit Terraform state or secrets. No backend is configured yet; do not use this starter as a production deployment.
