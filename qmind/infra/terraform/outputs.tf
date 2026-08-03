output "ecr_api_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "ecr_web_repository_url" {
  value = aws_ecr_repository.web.repository_url
}

output "ecr_worker_repository_url" {
  value = aws_ecr_repository.worker.repository_url
}

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

output "rds_endpoint" {
  value     = aws_db_instance.main.address
  sensitive = false
}

output "rds_security_group_id" {
  value = aws_security_group.rds.id
}

output "app_secret_arn" {
  value = aws_secretsmanager_secret.app.arn
}
