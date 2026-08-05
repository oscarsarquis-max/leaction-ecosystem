terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # backend "s3" {
  #   bucket = "leaction-tfstate"
  #   key    = "qmind/homolog-minimal-ec2/terraform.tfstate"
  #   region = "us-east-2"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "qmind"
      Environment = var.environment
      ManagedBy   = "terraform"
      Profile     = "minimal-ec2"
      Baseline    = "mvp-fullstack-v0"
      ADR         = "ADR-010"
    }
  }
}
