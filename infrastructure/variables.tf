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


variable "ecs_task_cpu" {
  description = "Fargate task CPU units. 256 represents 0.25 vCPU."
  type        = number
  default     = 256

  validation {
    condition     = contains([256, 512, 1024], var.ecs_task_cpu)
    error_message = "For this demo, ecs_task_cpu must be 256, 512, or 1024."
  }
}

variable "ecs_task_memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 512

  validation {
    condition     = contains([512, 1024, 2048], var.ecs_task_memory)
    error_message = "For this demo, ecs_task_memory must be 512, 1024, or 2048 MiB."
  }
}

variable "private_db_subnet_cidrs" {
  description = "CIDR ranges for private database subnets."
  type        = list(string)
  default     = ["10.20.21.0/24", "10.20.22.0/24"]

  validation {
    condition     = length(var.private_db_subnet_cidrs) == 2
    error_message = "Provide exactly two private database subnet CIDRs."
  }
}

variable "db_name" {
  description = "PostgreSQL database name."
  type        = string
  default     = "cloudcapsule"
}

variable "db_username" {
  description = "PostgreSQL master username."
  type        = string
  default     = "cloudcapsule"
}

variable "db_instance_class" {
  description = "RDS instance class for the budget-conscious demo."
  type        = string
  default     = "db.t3.micro"
}