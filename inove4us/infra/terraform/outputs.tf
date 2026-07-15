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
  description = "Use este SG como origem no RDS (já aplicado via aws_security_group_rule.rds_from_inove4us)"
  value       = aws_security_group.ecs_tasks.id
}

output "public_urls" {
  value = {
    apex = "https://${var.domain_name}"
    www  = "https://www.${var.domain_name}"
  }
}
