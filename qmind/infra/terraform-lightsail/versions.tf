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
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "qmind"
      Environment = var.environment
      ManagedBy   = "terraform"
      Profile     = "lightsail"
      Baseline    = "mvp-fullstack-v0"
      ADR         = "ADR-010"
    }
  }
}
