terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }
}

provider "aws" {
  region = "us-east-2"
  default_tags {
    tags = {
      Project     = "spider"
      Environment = "sandbox"
      ManagedBy   = "terraform"
      Domain      = "spider.actionhub.com.br"
    }
  }
}
