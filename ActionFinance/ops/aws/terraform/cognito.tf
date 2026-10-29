resource "aws_cognito_user_pool" "this" {
  count = var.enable_cognito ? 1 : 0
  name  = "${var.name_prefix}-operators"

  # Login is a username (may look like an email). Contact email is a separate attribute.
  # Do not set username_attributes=email or alias_attributes=email: that would force
  # the sign-in identifier to be the contact mailbox.
  auto_verified_attributes = ["email"]
  mfa_configuration        = "OPTIONAL"

  username_configuration {
    case_sensitive = false
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true
  }

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 1
  }

  software_token_mfa_configuration { enabled = true }

  tags = { Product = "actionfinance" }
}

resource "aws_cognito_user_pool_domain" "this" {
  count        = var.enable_cognito ? 1 : 0
  domain       = "${var.name_prefix}-${var.aws_account_id}"
  user_pool_id = aws_cognito_user_pool.this[0].id
}

resource "aws_cognito_user_pool_client" "this" {
  count        = var.enable_cognito ? 1 : 0
  name         = "${var.name_prefix}-confidential"
  user_pool_id = aws_cognito_user_pool.this[0].id

  generate_secret                      = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = ["${var.public_origin}/login/oauth2/code/actionfinance"]
  logout_urls                          = [var.public_origin]
  prevent_user_existence_errors        = "ENABLED"
  explicit_auth_flows                  = ["ALLOW_REFRESH_TOKEN_AUTH"]
}
