output "classification" {
  value = "SANDBOX — not production"
}

output "parent_zone_id" {
  value = data.aws_route53_zone.parent.zone_id
}

output "parent_zone_name" {
  value = data.aws_route53_zone.parent.name
}

output "spider_zone_id" {
  value = module.dns.zone_id
}

output "spider_name_servers" {
  value = module.dns.name_servers
}

output "monitor_hostname" {
  value = "monitor.spider.actionhub.com.br"
}

output "api_hostname" {
  value = "api.spider.actionhub.com.br"
}

output "callbacks_hostname" {
  value = "callbacks.spider.actionhub.com.br"
}

output "ecr_repository_url" {
  value = module.compute.ecr_repository_url
}

output "frontend_bucket" {
  value = module.frontend.bucket_name
}

output "cloudfront_distribution_id" {
  value = module.frontend.distribution_id
}

output "persistence_mode" {
  value = var.enable_database ? "monitor-jpa-ready (canonical memory)" : "memory (RDS module disabled)"
}

output "monitor_database_endpoint" {
  value = module.database.endpoint
}

output "monitor_database_secret_arn" {
  value = module.database.secret_arn
}

output "cluster_name" {
  value = module.compute.cluster_name
}

output "service_name" {
  value = module.compute.service_name
}

output "task_definition_arn" {
  value = module.compute.task_definition_arn
}

output "target_group_arn" {
  value = module.compute.target_group_arn
}

output "image_tag" {
  value = var.image_tag
}

output "monitor_identity_provider" {
  value = "cognito-user-pool-sandbox"
}

output "monitor_user_pool_id" {
  value = module.identity.user_pool_id
}

output "monitor_app_client_id" {
  value = module.identity.client_id
}

output "monitor_hosted_ui" {
  value = module.identity.hosted_ui_domain
}

output "monitor_operator_group" {
  value = module.identity.operator_group_name
}

output "monitor_oidc_lambda_version" {
  value = module.frontend.oidc_lambda_version_arn
}

output "monitor_ip_fallback_enabled" {
  value = module.frontend.monitor_ip_fallback_enabled
}
