output "ecr_repository_url" {
  value = aws_ecr_repository.inove4us.repository_url
}

output "alb_dns_name" {
  value = aws_lb.inove4us.dns_name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.inove4us.name
}

output "ecs_service_name" {
  value = aws_ecs_service.inove4us.name
}

output "ecs_tasks_security_group_id" {
  description = "SG das tasks Fargate"
  value       = aws_security_group.ecs_tasks.id
}

output "rds_endpoint" {
  description = "Endpoint do RDS dedicado (vazio se create_dedicated_rds=false)"
  value       = var.create_dedicated_rds ? aws_db_instance.inove4us[0].address : null
}

output "rds_db_name" {
  value = var.create_dedicated_rds ? aws_db_instance.inove4us[0].db_name : null
}

output "rds_security_group_id" {
  value = var.create_dedicated_rds ? aws_security_group.rds[0].id : null
}

output "db_secret_arn" {
  value = var.create_dedicated_rds ? aws_secretsmanager_secret.inove4us_db[0].arn : null
}

output "public_urls" {
  value = {
    apex = "https://${var.domain_name}"
    www  = "https://www.${var.domain_name}"
  }
}
