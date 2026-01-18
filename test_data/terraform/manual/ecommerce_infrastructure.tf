# Production E-Commerce Platform Infrastructure
# Team: Platform Engineering
# Date: 2024-01-15

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Customer Data Storage
resource "aws_s3_bucket" "customer_data" {
  bucket = "prod-customer-data-2024"
  force_destroy = true
  
  tags = {
    Environment = "production"
    DataClass = "sensitive"
    Team = "data-engineering"
  }
}

resource "aws_s3_bucket_versioning" "customer_data_versioning" {
  bucket = aws_s3_bucket.customer_data.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Order Processing Database
resource "aws_db_instance" "orders_db" {
  identifier = "production-orders-database"
  engine = "postgres"
  engine_version = "15.3"
  instance_class = "db.r6g.xlarge"
  allocated_storage = 500
  
  db_name = "orders_prod"
  username = "orderadmin"
  password = "PLACEHOLDER_USE_SECRETS_MANAGER"
  
  backup_retention_period = 30
  backup_window = "03:00-04:00"
  maintenance_window = "sun:04:00-sun:05:00"
  
  multi_az = true
  storage_encrypted = true
  
  lifecycle {
    prevent_destroy = true
  }
  
  tags = {
    Environment = "production"
    Critical = "true"
    Application = "order-processing"
  }
}

# Payment Processing Database
resource "aws_db_instance" "payments_db" {
  identifier = "production-payments-db"
  engine = "postgres"
  engine_version = "15.3"
  instance_class = "db.r6g.2xlarge"
  allocated_storage = 1000
  
  db_name = "payments_prod"
  username = "paymentadmin"
  password = "PLACEHOLDER_USE_SECRETS_MANAGER"
  
  backup_retention_period = 35
  multi_az = true
  storage_encrypted = true
  
  tags = {
    Environment = "production"
    Critical = "true"
    Compliance = "PCI-DSS"
  }
}

# Product Catalog Storage
resource "aws_s3_bucket" "product_images" {
  bucket = "prod-product-images-cdn"
  
  lifecycle {
    prevent_destroy = true
  }
  
  tags = {
    Environment = "production"
    CDN = "cloudfront"
  }
}

# Session Data Store
resource "aws_dynamodb_table" "user_sessions" {
  name = "production-user-sessions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "session_id"
  
  attribute {
    name = "session_id"
    type = "S"
  }
  
  ttl {
    attribute_name = "expiry_time"
    enabled = true
  }
  
  point_in_time_recovery {
    enabled = true
  }
  
  tags = {
    Environment = "production"
  }
}

# Analytics Data Warehouse
resource "aws_s3_bucket" "analytics_data" {
  bucket = "prod-analytics-warehouse-2024"
  
  tags = {
    Environment = "production"
    DataRetention = "7years"
    Team = "analytics"
  }
}

# Legacy Testing Bucket - To Be Removed
resource "aws_s3_bucket" "legacy_test_bucket" {
  bucket = "old-testing-bucket-2023"
  force_destroy = true
  
  lifecycle {
    prevent_destroy = false
  }
  
  tags = {
    Environment = "test"
    Deprecated = "true"
  }
}

# Web Application Auto Scaling Group
resource "aws_autoscaling_group" "web_app" {
  name = "production-web-app-asg"
  min_size = 3
  max_size = 10
  desired_capacity = 5
  
  vpc_zone_identifier = ["subnet-abc123", "subnet-def456"]
  
  launch_template {
    id = aws_launch_template.web_app.id
    version = "$Latest"
  }
  
  tag {
    key = "Environment"
    value = "production"
    propagate_at_launch = true
  }
}

resource "aws_launch_template" "web_app" {
  name = "production-web-app-template"
  image_id = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.large"
  
  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "production-web-server"
      Environment = "production"
    }
  }
}

# IAM Role for Application
resource "aws_iam_role" "app_role" {
  name = "production-app-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

# Cleanup Script for Development Resources
resource "null_resource" "cleanup_dev_resources" {
  provisioner "local-exec" {
    command = "terraform destroy -auto-approve -target=aws_s3_bucket.dev_test_bucket"
  }
  
  triggers = {
    cleanup_schedule = "monthly"
  }
}

# Temporary Worker Instances (Scaled Down)
resource "aws_instance" "batch_workers" {
  ami = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.medium"
  count = 0
  
  tags = {
    Name = "batch-worker"
    Environment = "production"
    Role = "background-processing"
  }
}
