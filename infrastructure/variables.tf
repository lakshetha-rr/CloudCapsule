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

variable "vpc_cidr" {
  description = "CIDR range for the CloudCapsule VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR ranges for the two public subnets."
  type        = list(string)
  default     = ["10.20.1.0/24", "10.20.2.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Provide exactly two public subnet CIDRs."
  }
}

variable "private_app_subnet_cidrs" {
  description = "CIDR ranges for the two private application subnets."
  type        = list(string)
  default     = ["10.20.11.0/24", "10.20.12.0/24"]

  validation {
    condition     = length(var.private_app_subnet_cidrs) == 2
    error_message = "Provide exactly two private application subnet CIDRs."
  }
}
