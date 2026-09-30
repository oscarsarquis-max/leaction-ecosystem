terraform {
  backend "s3" {
    bucket         = "spider-sandbox-tfstate-253137917703"
    key            = "spider/sandbox/terraform.tfstate"
    region         = "us-east-2"
    dynamodb_table = "spider-sandbox-tf-lock"
    encrypt        = true
  }
}
