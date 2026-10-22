resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnets"
  subnet_ids = aws_subnet.private_db[*].id

  tags = {
    Name      = "${local.name_prefix}-db-subnets"
    Project   = var.project_name
    ManagedBy = "Terraform"
  }
}

resource "aws_db_instance" "postgres" {
  identifier = "${local.name_prefix}-postgres"

  engine         = "postgres"
  instance_class = var.db_instance_class

  db_name  = var.db_name
  username = var.db_username

  manage_master_user_password = true

  allocated_storage     = 20
  max_allocated_storage = 30
  storage_type          = "gp3"
  storage_encrypted     = true

  multi_az                = false
  publicly_accessible     = false
  backup_retention_period = 1

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.database.id]

  auto_minor_version_upgrade = true
  deletion_protection        = true
  skip_final_snapshot        = false
  final_snapshot_identifier  = "${local.name_prefix}-postgres-final"

  tags = {
    Name      = "${local.name_prefix}-postgres"
    Project   = var.project_name
    ManagedBy = "Terraform"
  }
}

output "rds_endpoint" {
  description = "Endpoint hostname for the planned PostgreSQL database."
  value       = aws_db_instance.postgres.address
}

output "rds_secret_arn" {
  description = "ARN of the RDS-managed master credential secret."
  value       = aws_db_instance.postgres.master_user_secret[0].secret_arn
}