# Credenciais do Postgres compartilhado (mesmo secret do PanelDX)
data "aws_secretsmanager_secret_version" "paneldx_db" {
  secret_id = var.db_secret_id
}

locals {
  db_secret = jsondecode(data.aws_secretsmanager_secret_version.paneldx_db.secret_string)

  db_host = coalesce(try(local.db_secret.host, null), var.secrets.db_host)
  db_port = tostring(coalesce(try(local.db_secret.port, null), var.secrets.db_port))
  # Prefer var.secrets.db_name: o secret paneldx-db-credentials usa dbname=paneldx_db
  # (vazio), enquanto as tabelas ctdi_* do PanelDX ficam em LeAction_SysF.
  db_name = coalesce(
    var.secrets.db_name != "" ? var.secrets.db_name : null,
    try(local.db_secret.dbname, null),
    "LeAction_SysF",
  )
  db_user = coalesce(try(local.db_secret.username, null), var.secrets.db_user)
  db_pass = coalesce(try(local.db_secret.password, null), var.secrets.db_pass)

  app_secret_key = var.secrets.secret_key != "" && var.secrets.secret_key != "CHANGE_ME_LONG_RANDOM_SECRET" ? var.secrets.secret_key : random_password.app_secret.result
}

resource "random_password" "app_secret" {
  length  = 48
  special = false
}
