resource "aws_secretsmanager_secret" "app" {
  name_prefix = "${var.name_prefix}-app-"
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    DATABASE_URL_ADMIN = format(
      "postgresql+psycopg://%s:%s@%s:5432/%s",
      var.db_master_username,
      random_password.db_master.result,
      aws_db_instance.main.address,
      var.db_name,
    )
    # Runtime URL must be rotated to qmind_app after bootstrap SQL — placeholder:
    DATABASE_URL_APP = format(
      "postgresql+psycopg://qmind_app:CHANGE_ME@%s:5432/%s",
      aws_db_instance.main.address,
      var.db_name,
    )
    AUTH_MODE                     = "cognito"
    COGNITO_REGION                = var.aws_region
    COGNITO_USER_POOL_ID          = aws_cognito_user_pool.main.id
    COGNITO_APP_CLIENT_ID         = aws_cognito_user_pool_client.web.id
    STORAGE_BACKEND               = "s3"
    S3_BUCKET                     = aws_s3_bucket.evidence.bucket
    S3_REGION                     = var.aws_region
    ALLOW_SIMULATED_SECURITY_PASS = "false"
    ENVIRONMENT                   = var.environment
  })
}
