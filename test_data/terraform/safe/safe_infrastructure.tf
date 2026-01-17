resource "aws_s3_bucket" "logs_bucket" {
  bucket = "my-application-logs"
  
  lifecycle {
    prevent_destroy = true
  }
  
  versioning {
    enabled = true
  }
  
  tags = {
    Environment = "production"
    Purpose = "application-logs"
  }
}

resource "aws_db_instance" "safe_db" {
  identifier = "app-database"
  engine = "postgres"
  instance_class = "db.t3.small"
  
  lifecycle {
    prevent_destroy = true
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners = ["099720109477"]
  
  filter {
    name = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}
