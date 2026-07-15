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

  # Descomente após criar o bucket de state
  # backend "s3" {
  #   bucket = "leaction-tfstate"
  #   key    = "inove4us/prod/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  # PanelDX / RDS LeAction_SysF vivem em us-east-2
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "inove4us"
      Environment = var.environment
      ManagedBy   = "terraform"
      Domain      = "inove4us.com.br"
    }
  }
}
