# Data Pipeline Infrastructure
# Team: Data Engineering
# Purpose: ETL pipeline for customer analytics

terraform {
  required_version = ">= 1.0"
}

# Raw Data Lake
resource "aws_s3_bucket" "raw_data_lake" {
  bucket = "prod-raw-data-lake-2024"
  force_destroy = true
  
  tags = {
    Environment = "production"
    DataStage = "raw"
    RetentionYears = "10"
  }
}

resource "aws_s3_bucket_versioning" "raw_data_versioning" {
  bucket = aws_s3_bucket.raw_data_lake.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Processed Data Storage
resource "aws_s3_bucket" "processed_data" {
  bucket = "prod-processed-data-2024"
  
  lifecycle {
    prevent_destroy = true
  }
  
  tags = {
    Environment = "production"
    DataStage = "processed"
    Critical = "true"
  }
}

# Data Warehouse Database
resource "aws_redshift_cluster" "analytics_warehouse" {
  cluster_identifier = "prod-analytics-cluster"
  database_name = "analytics"
  master_username = "analytics_admin"
  master_password = "PLACEHOLDER_CHANGE_ME"
  node_type = "ra3.4xlarge"
  number_of_nodes = 4
  
  encrypted = true
  
  tags = {
    Environment = "production"
    CostCenter = "analytics"
  }
}

# Metadata Catalog
resource "aws_glue_catalog_database" "data_catalog" {
  name = "production_data_catalog"
  
  description = "Central metadata catalog for all data assets"
}

# ETL Job Definitions
resource "aws_glue_job" "customer_etl" {
  name = "prod-customer-data-etl"
  role_arn = aws_iam_role.glue_role.arn
  
  command {
    script_location = "s3://scripts-bucket/customer_etl.py"
    python_version = "3"
  }
  
  max_retries = 3
  timeout = 60
  
  tags = {
    Environment = "production"
    Pipeline = "customer-analytics"
  }
}

# Streaming Data Store
resource "aws_dynamodb_table" "streaming_events" {
  name = "production-streaming-events"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "event_id"
  range_key = "timestamp"
  
  attribute {
    name = "event_id"
    type = "S"
  }
  
  attribute {
    name = "timestamp"
    type = "N"
  }
  
  stream_enabled = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  
  tags = {
    Environment = "production"
    DataType = "streaming"
  }
}

# Temporary Staging Buckets
resource "aws_s3_bucket" "staging_temp" {
  bucket = "temp-staging-data-2024"
  
  lifecycle {
    prevent_destroy = false
  }
  
  tags = {
    Environment = "staging"
    Temporary = "true"
  }
}

# Machine Learning Model Storage
resource "aws_s3_bucket" "ml_models" {
  bucket = "prod-ml-models-2024"
  
  tags = {
    Environment = "production"
    Team = "ml-engineering"
    Critical = "true"
  }
}

# Data Processing Cluster
resource "aws_emr_cluster" "data_processing" {
  name = "prod-data-processing-cluster"
  release_label = "emr-6.15.0"
  applications = ["Spark", "Hadoop"]
  
  ec2_attributes {
    instance_profile = aws_iam_instance_profile.emr_profile.arn
    subnet_id = "subnet-xyz789"
  }
  
  master_instance_group {
    instance_type = "m5.xlarge"
    instance_count = 1
  }
  
  core_instance_group {
    instance_type = "m5.2xlarge"
    instance_count = 0
  }
  
  service_role = aws_iam_role.emr_role.arn
  
  tags = {
    Environment = "production"
    Application = "data-processing"
  }
}

# IAM Roles
resource "aws_iam_role" "glue_role" {
  name = "prod-glue-service-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "glue.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role" "emr_role" {
  name = "prod-emr-service-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "elasticmapreduce.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_instance_profile" "emr_profile" {
  name = "prod-emr-instance-profile"
  role = aws_iam_role.emr_role.name
}

# Backup and Archive Storage
resource "aws_s3_bucket" "data_archive" {
  bucket = "prod-data-archive-glacier"
  
  lifecycle {
    prevent_destroy = true
  }
  
  tags = {
    Environment = "production"
    StorageClass = "glacier"
    RetentionPolicy = "permanent"
  }
}

# Development Testing Resources Cleanup
resource "null_resource" "cleanup_old_pipelines" {
  provisioner "local-exec" {
    command = "terraform destroy -target=module.dev_pipeline"
  }
}
