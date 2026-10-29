terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_vpc" "this" { id = var.vpc_id }
data "aws_route53_zone" "public" { zone_id = var.hosted_zone_id }

locals {
  origin_host = trimprefix(trimsuffix(replace(var.public_origin, "https://", ""), "/"), "")
  serve       = var.image_uri != ""
}

check "target_account" {
  assert {
    condition     = data.aws_caller_identity.current.account_id == var.aws_account_id
    error_message = "Provider caller account does not match var.aws_account_id. Refusing to plan against the wrong account."
  }
}

check "not_sandbox_vpc" {
  assert {
    condition     = var.vpc_id != "vpc-0048417ebcf7b7447"
    error_message = "Spider sandbox VPC is not an ActionFinance production target."
  }
}

check "dns_zone_name" {
  assert {
    condition     = trimsuffix(data.aws_route53_zone.public.name, ".") == "actionhub.com.br"
    error_message = "hosted_zone_id must remain the public actionhub.com.br zone."
  }
}
