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

  # Após criar bucket de state do ecossistema:
  # backend "s3" {
  #   bucket = "leaction-tfstate"
  #   key    = "qmind/homolog/terraform.tfstate"
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
      Baseline    = "mvp-fullstack-v0"
    }
  }
}
