output "vpc_id" {
  value = module.network.vpc_id
}

output "alb_dns_name" {
  value = module.compute.alb_dns_name
}

output "ecr_repository_url" {
  value = module.compute.ecr_repository_url
}

output "cluster_name" {
  value = module.compute.cluster_name
}

output "runtime_service_name" {
  value = aws_ecs_service.runtime.name
}

output "database_endpoint" {
  value = module.database.endpoint
}

output "monitor_distribution" {
  value = module.frontend.distribution_domain
}

output "monitor_bucket" {
  value = "${local.name_prefix}-monitor-web"
}

output "canary_api" {
  value = local.api_hostname
}

output "canary_monitor" {
  value = local.monitor_hostname
}

output "actionfinance_secret_arn" {
  value = aws_secretsmanager_secret.actionfinance.arn
}

output "pay_secret_name" {
  value = aws_secretsmanager_secret.pay.name
}
