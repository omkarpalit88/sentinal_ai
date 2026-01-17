resource "null_resource" "cleanup_old_resources" {
  provisioner "local-exec" {
    command = "terraform destroy -auto-approve -target=module.old_staging"
  }
}

resource "null_resource" "remove_test_data" {
  provisioner "local-exec" {
    command = "terraform destroy -target=aws_s3_bucket.test_data"
  }
}

resource "aws_instance" "temp_worker" {
  ami = "ami-12345678"
  instance_class = "t3.micro"
  
  provisioner "local-exec" {
    when = "destroy"
    command = "terraform destroy -auto-approve"
  }
}
