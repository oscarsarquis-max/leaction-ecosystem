terraform {
  backend "s3" {
    bucket         = "spider-prod-tfstate-253137917703"
    key            = "spider/production/terraform.tfstate"
    region         = "us-east-2"
    dynamodb_table = "spider-prod-tf-lock"
    encrypt        = true
  }
}
