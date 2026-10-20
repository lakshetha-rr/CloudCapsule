variable "aws_region" {
  description = "AWS region for a future reviewed deployment."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Short project name used in resource naming."
  type        = string
  default     = "cloudcapsule"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "demo"

  validation {
    condition     = contains(["dev", "demo", "staging", "prod"], var.environment)
    error_message = "environment must be dev, demo, staging, or prod."
  }
}

variable "monthly_budget_inr" {
  description = "User-defined budget target; not an AWS billing control by itself."
  type        = number
  default     = 3000

  validation {
    condition     = var.monthly_budget_inr > 0
    error_message = "monthly_budget_inr must be greater than zero."
  }
}
