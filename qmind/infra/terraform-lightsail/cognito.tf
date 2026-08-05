resource "random_id" "suffix" {
  byte_length = 3
}

resource "aws_cognito_user_pool" "main" {
  name = "${var.name_prefix}-users"

  deletion_protection      = "ACTIVE"
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  mfa_configuration        = "OPTIONAL"

  # Piloto: apenas usuários convidados (admin create).
  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  software_token_mfa_configuration {
    enabled = true
  }

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true
  }
}

resource "aws_cognito_user_pool_client" "web" {
  name         = "${var.name_prefix}-web"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = var.cognito_callback_urls
  logout_urls                          = var.cognito_logout_urls

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
    # Homolog gate / ops: AdminInitiateAuth for controlled E2E (no secret in git).
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
  ]

  prevent_user_existence_errors = "ENABLED"
}

resource "aws_cognito_user_pool_domain" "main" {
  domain                = "${var.name_prefix}-${random_id.suffix.hex}"
  user_pool_id          = aws_cognito_user_pool.main.id
  # 2 = Managed Login (localização pt-BR via ?lang=pt-BR). 1 = Hosted UI clássico.
  managed_login_version = 2
}

# Branding Managed Login (defaults Cognito) — criado/associado ao client web.
# Provider AWS 5.x: manter via CLI se o recurso TF ainda não estiver disponível:
#   aws cognito-idp create-managed-login-branding \
#     --user-pool-id … --client-id … --use-cognito-provided-values

