resource "aws_s3_bucket" "data_bucket" {
  bucket = "my-critical-data-bucket"
  
  # CRITICAL RISK: force_destroy allows data loss
  force_destroy = true
  
  versioning {
    enabled = true
  }
}

resource "aws_db_instance" "production_db" {
  identifier = "prod-database"
  engine = "postgres"
  instance_class = "db.t3.medium"
  
  # HIGH RISK: prevent_destroy disabled
  lifecycle {
    prevent_destroy = false
  }
  
  skip_final_snapshot = true
}

# HIGH RISK: Resource count set to 0 (removes infrastructure)
resource "aws_instance" "web_server" {
  ami = "ami-12345678"
  instance_type = "t3.micro"
  count = 0
}
