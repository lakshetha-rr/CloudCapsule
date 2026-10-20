
resource "aws_ecr_repository" "backend" {
  name                 = "${local.name_prefix}-backend"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name      = "${local.name_prefix}-backend"
    Project   = var.project_name
    ManagedBy = "Terraform"
  }
}

output "backend_ecr_repository_url" {
  description = "URL of the planned backend container image repository."
  value       = aws_ecr_repository.backend.repository_url
}
