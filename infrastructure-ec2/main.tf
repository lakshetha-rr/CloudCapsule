
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"
}

variable "allowed_cidr" {
  description = "Your public IPv4 address in CIDR notation"
  type        = string

  validation {
    condition     = can(cidrhost(var.allowed_cidr, 0)) && can(regex("/32$", var.allowed_cidr)) && !strcontains(var.allowed_cidr, ":")
    error_message = "allowed_cidr must be a single IPv4 address ending in /32."
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_vpc" "main" {
  cidr_block           = "10.30.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "cloudcapsule-demo-vpc" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.30.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = { Name = "cloudcapsule-demo-public" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = { Name = "cloudcapsule-demo-igw" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "cloudcapsule-demo-public-rt" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "app" {
  name        = "cloudcapsule-demo-app-sg"
  description = "Restrict CloudCapsule demo API to the configured IPv4 address"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "CloudCapsule API from allowed IPv4 address"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "cloudcapsule-demo-app-sg" }
}

resource "aws_instance" "app" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = "t3.micro"
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.app.id]
  associate_public_ip_address = true

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    volume_size           = 12
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  user_data = <<-USERDATA
    #!/bin/bash
    set -euxo pipefail
    exec > >(tee -a /var/log/cloudcapsule-setup.log) 2>&1

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose-v2 git
    systemctl enable --now docker

    git clone https://github.com/lakshetha-rr/CloudCapsule.git /opt/CloudCapsule
    cd /opt/CloudCapsule

    DB_PASSWORD="$(openssl rand -hex 24)"
    cat > .env <<ENV
    DATABASE_URL=postgresql://cloudcapsule:$${DB_PASSWORD}@db:5432/cloudcapsule
    POSTGRES_PASSWORD=$${DB_PASSWORD}
    ENV
    chmod 600 .env

    sed -i 's/127.0.0.1:8000:8000/8000:8000/' compose.yaml
    docker compose up -d --build
  USERDATA

  tags = {
    Name      = "cloudcapsule-demo"
    Project   = "cloudcapsule"
    ManagedBy = "Terraform"
  }
}

output "app_url" {
  description = "CloudCapsule API URL; wait for setup before opening."
  value       = "http://${aws_instance.app.public_ip}:8000"
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.app.id
}
