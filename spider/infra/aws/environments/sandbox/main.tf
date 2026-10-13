locals {
  name_prefix                = "spider-sandbox"
  zone_name                  = "spider.actionhub.com.br"
  sandbox_allowed_ipv4_cidrs = distinct(concat(var.sandbox_allowed_ipv4_cidrs, var.allowed_cidr_blocks))
  sandbox_allowed_ipv6_cidrs = var.sandbox_allowed_ipv6_cidrs
  tags = {
    Project     = "spider"
    Environment = "sandbox"
    ManagedBy   = "terraform"
    Domain      = "spider.actionhub.com.br"
    Class       = "SANDBOX"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_route53_zone" "parent" {
  zone_id = var.parent_zone_id
}

module "dns" {
  source    = "../../modules/dns"
  zone_name = local.zone_name
  tags      = local.tags
}

# ÚNICA alteração na zona pai actionhub.com.br: delegação NS de spider.
resource "aws_route53_record" "spider_delegation" {
  zone_id = data.aws_route53_zone.parent.zone_id
  name    = local.zone_name
  type    = "NS"
  ttl     = 300
  records = module.dns.name_servers
}

module "certificate_regional" {
  source                    = "../../modules/certificates"
  zone_id                   = module.dns.zone_id
  domain_name               = local.zone_name
  subject_alternative_names = ["*.${local.zone_name}"]
  tags                      = local.tags
}

module "certificate_cloudfront" {
  source                    = "../../modules/certificates"
  providers                 = { aws = aws.us_east_1 }
  zone_id                   = module.dns.zone_id
  domain_name               = local.zone_name
  subject_alternative_names = ["*.${local.zone_name}"]
  tags                      = local.tags
}

module "network" {
  source      = "../../modules/network"
  name_prefix = local.name_prefix
  azs         = slice(data.aws_availability_zones.available.names, 0, 2)
  enable_nat  = false
  tags        = local.tags
}

resource "random_password" "origin_verify" {
  length  = 48
  special = false
}

resource "random_password" "edge_state" {
  length  = 48
  special = false
}

data "aws_ec2_managed_prefix_list" "cloudfront_origin" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

module "identity" {
  source           = "../../modules/identity"
  name_prefix      = local.name_prefix
  monitor_hostname = "monitor.${local.zone_name}"
  tags             = local.tags
}

module "compute" {
  source                           = "../../modules/compute"
  name_prefix                      = local.name_prefix
  vpc_id                           = module.network.vpc_id
  public_subnet_ids                = module.network.public_subnet_ids
  private_subnet_ids               = module.network.private_subnet_ids
  acm_certificate_arn              = module.certificate_regional.certificate_arn
  desired_count                    = var.desired_count
  assign_public_ip                 = true
  image_tag                        = var.image_tag
  sandbox_allowed_ipv4_cidrs       = local.sandbox_allowed_ipv4_cidrs
  sandbox_allowed_ipv6_cidrs       = local.sandbox_allowed_ipv6_cidrs
  cloudfront_origin_prefix_list_id = data.aws_ec2_managed_prefix_list.cloudfront_origin.id
  origin_verify_secret             = random_password.origin_verify.result
  actionfinance_nat_ipv4_cidrs     = var.actionfinance_nat_ipv4_cidrs
  tags                             = local.tags
}

module "frontend" {
  source                      = "../../modules/frontend"
  providers                   = { aws = aws.us_east_1 }
  name_prefix                 = local.name_prefix
  monitor_hostname            = "monitor.${local.zone_name}"
  apex_hostname               = local.zone_name
  acm_certificate_arn         = module.certificate_cloudfront.certificate_arn
  sandbox_allowed_ipv4_cidrs  = local.sandbox_allowed_ipv4_cidrs
  sandbox_allowed_ipv6_cidrs  = local.sandbox_allowed_ipv6_cidrs
  api_origin_hostname         = "api.${local.zone_name}"
  origin_verify_secret        = random_password.origin_verify.result
  oidc_user_pool_id           = module.identity.user_pool_id
  oidc_client_id              = module.identity.client_id
  oidc_domain                 = module.identity.hosted_ui_domain
  oidc_issuer                 = module.identity.issuer
  oidc_group                  = module.identity.operator_group_name
  monitor_ip_fallback_enabled = var.monitor_ip_fallback_enabled
  edge_state_secret           = random_password.edge_state.result
  oidc_published_version      = var.oidc_published_version
  tags                        = local.tags
}

module "callbacks" {
  source              = "../../modules/callbacks"
  name_prefix         = local.name_prefix
  callbacks_hostname  = "callbacks.${local.zone_name}"
  acm_certificate_arn = module.certificate_regional.certificate_arn
  zone_id             = module.dns.zone_id
  tags                = local.tags
}

module "database" {
  source                = "../../modules/database"
  enabled               = var.enable_database
  name_prefix           = local.name_prefix
  vpc_id                = module.network.vpc_id
  private_subnet_ids    = module.network.private_subnet_ids
  app_security_group_id = module.compute.service_security_group_id
  kms_key_arn           = module.compute.kms_key_arn
  task_role_name        = module.compute.task_role_name
  execution_role_name   = module.compute.execution_role_name
  alarm_topic_arn       = module.observability.alarm_topic_arn
  tags                  = local.tags
}

module "observability" {
  source         = "../../modules/observability"
  name_prefix    = local.name_prefix
  alb_arn_suffix = module.compute.alb_arn_suffix
  tags           = local.tags
}

resource "aws_route53_record" "monitor" {
  zone_id = module.dns.zone_id
  name    = "monitor.${local.zone_name}"
  type    = "A"
  alias {
    name                   = module.frontend.distribution_domain
    zone_id                = module.frontend.distribution_hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "apex" {
  zone_id = module.dns.zone_id
  name    = local.zone_name
  type    = "A"
  alias {
    name                   = module.frontend.distribution_domain
    zone_id                = module.frontend.distribution_hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "api" {
  zone_id = module.dns.zone_id
  name    = "api.${local.zone_name}"
  type    = "A"
  alias {
    name                   = module.compute.alb_dns_name
    zone_id                = module.compute.alb_zone_id
    evaluate_target_health = true
  }
}
