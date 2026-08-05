# --- Pipeline / ECR ---

output "ecr_api_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "ecr_web_repository_url" {
  value = aws_ecr_repository.web.repository_url
}

output "ecr_worker_repository_url" {
  value = aws_ecr_repository.worker.repository_url
}

output "api_image_uri" {
  description = "URI efetiva usada na task definition"
  value       = local.api_image
}

# --- DNS / ALB / TLS ---

output "alb_dns_name" {
  description = "CNAME/alias target for Route 53"
  value       = aws_lb.api.dns_name
}

output "alb_zone_id" {
  description = "Hosted zone ID of the ALB (Route 53 alias)"
  value       = aws_lb.api.zone_id
}

output "alb_arn" {
  value = aws_lb.api.arn
}

output "target_group_arn" {
  value = aws_lb_target_group.api.arn
}

output "acm_certificate_arn" {
  description = "ARN used by the HTTPS listener"
  value       = local.acm_certificate_arn
}

output "acm_validation_records" {
  description = "DNS validation records when Terraform creates ACM"
  value = var.certificate_arn != "" ? [] : [
    for dvo in aws_acm_certificate.alb[0].domain_validation_options : {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  ]
}

# --- ECS ---

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  value = aws_ecs_cluster.main.arn
}

output "ecs_service_name" {
  value = aws_ecs_service.api.name
}

output "ecs_task_definition_arn" {
  value = aws_ecs_task_definition.api.arn
}

output "ecs_execution_role_arn" {
  value = aws_iam_role.ecs_execution.arn
}

output "ecs_task_role_arn" {
  value = aws_iam_role.ecs_task.arn
}

output "cloudwatch_log_group_api" {
  value = aws_cloudwatch_log_group.api.name
}

# --- Data / auth ---

output "evidence_bucket" {
  value = aws_s3_bucket.evidence.bucket
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.main.id
}

output "cognito_app_client_id" {
  value = aws_cognito_user_pool_client.web.id
}

output "cognito_domain" {
  value = aws_cognito_user_pool_domain.main.domain
}

output "cognito_issuer_url" {
  value = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.main.id}"
}

output "rds_endpoint" {
  value = aws_db_instance.main.address
}

output "rds_security_group_id" {
  value = aws_security_group.rds.id
}

output "ecs_security_group_id" {
  value = aws_security_group.ecs_tasks.id
}

output "alb_security_group_id" {
  value = aws_security_group.alb.id
}

output "app_secret_arn" {
  description = "Secrets Manager ARN (valores sensíveis não são outputs)"
  value       = aws_secretsmanager_secret.app.arn
}

output "alarm_sns_topic_arn" {
  value = length(local.alarm_actions) > 0 ? local.alarm_actions[0] : null
}

# --- Rollback helper ---

output "rollback_hints" {
  description = "Como reverter deployment sem destruir dados"
  value = {
    redeploy_previous_task_definition = "aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service ${aws_ecs_service.api.name} --task-definition <previous-family:revision> --force-new-deployment"
    circuit_breaker                   = "enabled with automatic rollback on failed deployment"
    baseline_image_tag                = var.api_image_tag
  }
}
