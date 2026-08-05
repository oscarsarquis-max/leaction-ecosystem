output "profile" {
  value = "minimal-ec2"
}

output "instance_id" {
  value = aws_instance.app.id
}

output "elastic_ip" {
  value = aws_eip.app.public_ip
}

output "public_dns_name" {
  value = var.domain_name
}

output "route53_fqdn" {
  value = try(aws_route53_record.app[0].fqdn, null)
}

output "evidence_bucket" {
  value = aws_s3_bucket.evidence.id
}

output "backup_bucket" {
  value = aws_s3_bucket.backups.id
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.main.id
}

output "cognito_client_id" {
  value = aws_cognito_user_pool_client.web.id
}

output "cognito_domain" {
  value = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "cognito_issuer" {
  value = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.main.id}"
}

output "ssm_start_session" {
  value = "aws ssm start-session --target ${aws_instance.app.id} --region ${var.aws_region}"
}

output "dns_pipeline_hints" {
  value = {
    a_record_target = aws_eip.app.public_ip
    health_url      = "https://${var.domain_name}/health"
    ready_url       = "https://${var.domain_name}/ready"
    compose_path    = "qmind/infra/compose/docker-compose.homolog.yml"
  }
}

output "restore_hints" {
  value = [
    "Criar snapshot do volume raiz da EC2 periodicamente.",
    "Agendar pg_dump → s3://${aws_s3_bucket.backups.id}/",
    "Testar restore em host efêmero antes de dados reais.",
  ]
}
