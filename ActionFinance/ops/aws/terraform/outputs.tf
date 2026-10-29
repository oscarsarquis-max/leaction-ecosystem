output "account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "alb_dns_name" {
  value = var.retire_dedicated_alb ? data.aws_lb.shared.dns_name : aws_lb.this[0].dns_name
}

output "shared_alb_dns_name" {
  value = data.aws_lb.shared.dns_name
}

output "ingress_alias" {
  value = var.ingress_alias
}

output "ecr_repository_url" {
  value = aws_ecr_repository.this.repository_url
}

output "rds_endpoint" {
  value = aws_db_instance.this.address
}

output "cognito_user_pool_id" {
  value = var.enable_cognito ? aws_cognito_user_pool.this[0].id : null
}

output "cognito_issuer" {
  value = var.enable_cognito ? "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.this[0].id}" : null
}

output "cognito_hosted_ui" {
  value = var.enable_cognito ? "https://${aws_cognito_user_pool_domain.this[0].domain}.auth.${var.aws_region}.amazoncognito.com" : null
}

output "public_host_enabled" {
  value = var.enable_public_dns
}

output "architecture" {
  value = "ALB TLS in ${var.aws_region} for ${local.origin_host}. Private Fargate in PanelDX VPC. Dedicated RDS. No CloudFront. Not applied until the owner approves DEP_001."
}
