variable "name_prefix" {
  type = string
}

variable "monitor_hostname" {
  type = string
}

variable "operator_group_name" {
  type    = string
  default = "spider-sandbox-operators"
}

variable "tags" {
  type    = map(string)
  default = {}
}

resource "aws_cognito_user_pool" "monitor" {
  name                     = "${var.name_prefix}-monitor"
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  mfa_configuration        = "OPTIONAL"
  deletion_protection      = "ACTIVE"

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 1
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  software_token_mfa_configuration {
    enabled = true
  }

  user_attribute_update_settings {
    attributes_require_verification_before_update = ["email"]
  }

  tags = var.tags
}

resource "aws_cognito_user_pool_domain" "monitor" {
  domain       = "${var.name_prefix}-monitor-${data.aws_caller_identity.current.account_id}"
  user_pool_id = aws_cognito_user_pool.monitor.id
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_cognito_user_pool_client" "monitor" {
  name         = "${var.name_prefix}-monitor-web"
  user_pool_id = aws_cognito_user_pool.monitor.id

  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = ["https://${var.monitor_hostname}/oauth/callback"]
  logout_urls = [
    "https://${var.monitor_hostname}/",
    "https://${var.monitor_hostname}/logout",
    "https://${var.monitor_hostname}/logged-out",
  ]
  prevent_user_existence_errors = "ENABLED"
  enable_token_revocation       = true
  access_token_validity         = 60
  id_token_validity             = 60
  refresh_token_validity        = 1
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]
}

resource "aws_cognito_user_group" "operators" {
  user_pool_id = aws_cognito_user_pool.monitor.id
  name         = var.operator_group_name
  description  = "Human operators allowed to use the Spider sandbox Monitor"
}

output "user_pool_id" {
  value = aws_cognito_user_pool.monitor.id
}

output "user_pool_arn" {
  value = aws_cognito_user_pool.monitor.arn
}

output "client_id" {
  value = aws_cognito_user_pool_client.monitor.id
}

output "hosted_ui_domain" {
  value = "https://${aws_cognito_user_pool_domain.monitor.domain}.auth.${data.aws_region.current.name}.amazoncognito.com"
}

output "issuer" {
  value = "https://cognito-idp.${data.aws_region.current.name}.amazonaws.com/${aws_cognito_user_pool.monitor.id}"
}

output "operator_group_name" {
  value = aws_cognito_user_group.operators.name
}

output "callback_url" {
  value = "https://${var.monitor_hostname}/oauth/callback"
}

output "logout_url" {
  value = "https://${var.monitor_hostname}/logout"
}
