resource "aws_s3_bucket" "data" {
  bucket = "critical-data-bucket"
  
  versioning {
    enabled = true
  }
  
  tags = {
    Environment = "production"
    Critical = "true"
  }
}

resource "aws_rds_db_instance" "prod" {
  identifier = "production-db"
  engine = "postgres"
  instance_class = "db.t3.large"
  allocated_storage = 100
  
  backup_retention_period = 7
  
  tags = {
    Environment = "production"
    Critical = "true"
  }
}

resource "aws_dynamodb_table" "sessions" {
  name = "user-sessions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "session_id"
  
  attribute {
    name = "session_id"
    type = "S"
  }
  
  tags = {
    Environment = "production"
  }
}
