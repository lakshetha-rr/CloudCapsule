provider "aws" {
  region = var.aws_region
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  proposed_components = {
    frontend       = "S3 private origin and CloudFront"
    api            = "ECS Fargate behind HTTPS ALB"
    database       = "Private RDS PostgreSQL"
    lifecycle_jobs = "SQS queue, DLQ, and ECS worker"
    secrets        = "Secrets Manager and KMS"
    observability  = "CloudWatch and CloudTrail"
    recovery       = "RDS backups, AWS Backup, and S3 versioning"
  }

  deployment_notice = "Design-only starter: no AWS resources are declared in this configuration."
}

output "architecture_summary" {
  description = "Proposed CloudCapsule components; informational only."
  value       = local.proposed_components
}

output "deployment_notice" {
  description = "Confirms this starter does not provision infrastructure."
  value       = local.deployment_notice
}

output "monthly_budget_target_inr" {
  description = "Planning target only; this does not configure AWS Budgets."
  value       = var.monthly_budget_inr
}
