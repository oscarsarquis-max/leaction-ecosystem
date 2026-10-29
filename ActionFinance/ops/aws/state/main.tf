# Bootstrap only. Creates the ActionFinance Terraform state bucket and lock table.
# Not applied in PRM_007 until the owner approves the plan. Do not import another product's state.

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}

variable "aws_account_id" {
  type    = string
  default = "253137917703"
}

variable "aws_region" {
  type    = string
  default = "us-east-2"
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

check "target_account" {
  assert {
    condition     = data.aws_caller_identity.current.account_id == var.aws_account_id
    error_message = "State bootstrap must run in the ActionFinance target account."
  }
}

resource "aws_s3_bucket" "state" {
  bucket = "actionfinance-tfstate-${var.aws_account_id}"

  tags = {
    Product = "actionfinance"
    Purpose = "terraform-state"
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    id     = "expire-noncurrent"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration { noncurrent_days = 90 }
  }
}

resource "aws_dynamodb_table" "lock" {
  name         = "actionfinance-tf-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Product = "actionfinance"
    Purpose = "terraform-lock"
  }
}

output "backend_bucket" { value = aws_s3_bucket.state.bucket }
output "lock_table" { value = aws_dynamodb_table.lock.name }
