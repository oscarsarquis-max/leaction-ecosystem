output "profile" {
  value = "lightsail"
}

output "lightsail_instance_name" {
  value = aws_lightsail_instance.app.name
}

output "static_ip" {
  value = aws_lightsail_static_ip.app.ip_address
}

output "api_hostname" {
  value = var.api_hostname
}

output "app_hostname" {
  value = var.app_hostname
}

output "pilot_api_hostname" {
  value = var.pilot_api_hostname
}

output "pilot_app_hostname" {
  value = var.pilot_app_hostname
}

output "pilot_www_hostname" {
  value = var.pilot_www_hostname
}

output "evidence_bucket" {
  value = aws_s3_bucket.evidence.id
}

output "backup_bucket" {
  value = aws_s3_bucket.backups.id
}

output "backup_prefix" {
  value = var.backup_prefix
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

# Nomes de usuários IAM apenas — NUNCA access keys neste output
output "iam_user_app_evidence" {
  value       = aws_iam_user.app_evidence.name
  description = "Criar access key fora do TF → /opt/qmind/secrets/app-evidence.env (0600)"
}

output "iam_user_backup_uploader" {
  value       = aws_iam_user.backup_uploader.name
  description = "Criar access key fora do TF → /opt/qmind/secrets/backup-uploader.env (0600)"
}

output "alarm_sns_topic_arn" {
  value = length(local.alarm_actions) > 0 ? local.alarm_actions[0] : null
}

output "alarm_email" {
  value = var.alarm_email
}

output "ops_hints" {
  value = {
    credentials_doc         = "qmind/infra/terraform-lightsail/CREDENTIALS.md"
    backup_script           = "qmind/infra/scripts/backup-pg-homolog.sh"
    restore_doc             = "qmind/infra/scripts/RESTORE_HOMOLOG.md"
    confirm_sns_email       = "Confirmar assinatura SNS em ${var.alarm_email}"
    confirm_lightsail_email = "Confirmar contato Lightsail Email em ${var.alarm_email}"
    lightsail_alarms        = "CFN stack native monitored_resource_name (CPU + StatusCheckFailed)"
    backup_alarm            = "CW BackupSuccess treat_missing_data=breaching até 1º dump OK"
    https                   = "Caddy + Let's Encrypt"
    postgres                = "sem porta pública"
    autosnapshot            = "Lightsail AutoSnapshot ${var.autosnapshot_time_utc} UTC"
    ssh                     = length(var.admin_ssh_cidrs) > 0 ? "restrito a admin_ssh_cidrs" : "fechado"
    budget                  = "qmind-homolog-monthly-30"
    no_keys_in_state        = "access keys nunca no Terraform"
  }
}
