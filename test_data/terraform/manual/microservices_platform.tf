# Microservices Platform Infrastructure
# Team: Platform SRE
# Services: API Gateway, Service Mesh, Monitoring

terraform {
  required_version = ">= 1.0"
}

# API Gateway Configuration Storage
resource "aws_s3_bucket" "api_configs" {
  bucket = "prod-api-gateway-configs"
  force_destroy = true
  
  tags = {
    Environment = "production"
    Service = "api-gateway"
  }
}

# Service Discovery Database
resource "aws_dynamodb_table" "service_registry" {
  name = "production-service-registry"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "service_name"
  
  attribute {
    name = "service_name"
    type = "S"
  }
  
  lifecycle {
    prevent_destroy = true
  }
  
  tags = {
    Environment = "production"
    Component = "service-discovery"
  }
}

# Authentication Service Database
resource "aws_rds_db_instance" "auth_service_db" {
  identifier = "prod-auth-service-db"
  engine = "mysql"
  engine_version = "8.0"
  instance_class = "db.t3.large"
  allocated_storage = 100
  
  db_name = "auth"
  username = "authadmin"
  password = "PLACEHOLDER"
  
  backup_retention_period = 14
  multi_az = true
  storage_encrypted = true
  
  tags = {
    Environment = "production"
    Service = "authentication"
    Critical = "true"
  }
}

# User Profile Service Database
resource "aws_rds_db_instance" "user_profile_db" {
  identifier = "prod-user-profile-db"
  engine = "postgres"
  engine_version = "15.3"
  instance_class = "db.r6g.large"
  allocated_storage = 200
  
  backup_retention_period = 21
  multi_az = true
  
  lifecycle {
    prevent_destroy = true
  }
  
  tags = {
    Environment = "production"
    Service = "user-profile"
  }
}

# Message Queue for Event Bus
resource "aws_sqs_queue" "event_bus" {
  name = "prod-event-bus-queue"
  
  message_retention_seconds = 1209600  # 14 days
  visibility_timeout_seconds = 300
  
  tags = {
    Environment = "production"
    Pattern = "event-driven"
  }
}

# Cache Layer
resource "aws_elasticache_cluster" "redis_cache" {
  cluster_id = "prod-redis-cache"
  engine = "redis"
  node_type = "cache.r6g.large"
  num_cache_nodes = 3
  parameter_group_name = "default.redis7"
  port = 6379
  
  tags = {
    Environment = "production"
    Component = "caching"
  }
}

# Container Registry
resource "aws_ecr_repository" "service_images" {
  name = "production-services"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  lifecycle {
    prevent_destroy = false
  }
  
  tags = {
    Environment = "production"
  }
}

# Monitoring and Logs Storage
resource "aws_s3_bucket" "application_logs" {
  bucket = "prod-application-logs-2024"
  
  tags = {
    Environment = "production"
    LogRetention = "90days"
  }
}

# Metrics Database
resource "aws_timestream_database" "metrics" {
  database_name = "production-metrics"
  
  tags = {
    Environment = "production"
    Component = "monitoring"
  }
}

# Load Balancer for Services
resource "aws_lb" "services_alb" {
  name = "prod-services-alb"
  internal = false
  load_balancer_type = "application"
  security_groups = ["sg-abc123"]
  subnets = ["subnet-1", "subnet-2"]
  
  enable_deletion_protection = true
  
  tags = {
    Environment = "production"
  }
}

# API Gateway Resources
resource "aws_api_gateway_rest_api" "main_api" {
  name = "production-api-gateway"
  
  endpoint_configuration {
    types = ["REGIONAL"]
  }
  
  tags = {
    Environment = "production"
    Gateway = "main"
  }
}

# Secrets Manager for Service Credentials
resource "aws_secretsmanager_secret" "service_secrets" {
  name = "prod/services/credentials"
  
  recovery_window_in_days = 30
  
  tags = {
    Environment = "production"
  }
}

# ECS Cluster for Microservices
resource "aws_ecs_cluster" "services_cluster" {
  name = "production-services-cluster"
  
  setting {
    name = "containerInsights"
    value = "enabled"
  }
  
  tags = {
    Environment = "production"
  }
}

# Notification Service Auto Scaling
resource "aws_ecs_service" "notification_service" {
  name = "notification-service"
  cluster = aws_ecs_cluster.services_cluster.id
  task_definition = "notification-task:latest"
  desired_count = 0
  
  tags = {
    Environment = "production"
    Service = "notifications"
  }
}

# Temporary Development Resources
resource "aws_s3_bucket" "dev_testing" {
  bucket = "temp-dev-testing-2024"
  force_destroy = true
  
  lifecycle {
    prevent_destroy = false
  }
  
  tags = {
    Environment = "development"
    Temporary = "true"
  }
}

# Cleanup Old Infrastructure
resource "null_resource" "infrastructure_cleanup" {
  provisioner "local-exec" {
    command = "terraform destroy -auto-approve -target=module.old_services"
    when = "destroy"
  }
}

# Service Mesh Control Plane
resource "aws_eks_cluster" "service_mesh" {
  name = "prod-service-mesh-cluster"
  role_arn = aws_iam_role.eks_role.arn
  
  vpc_config {
    subnet_ids = ["subnet-a", "subnet-b"]
  }
  
  tags = {
    Environment = "production"
    Component = "service-mesh"
  }
}

resource "aws_iam_role" "eks_role" {
  name = "prod-eks-cluster-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })
}
