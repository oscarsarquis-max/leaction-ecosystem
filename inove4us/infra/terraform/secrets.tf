# Credenciais DB — preferir RDS dedicado inove4us; fallback legado PanelDX só se create_dedicated_rds=false

data "aws_secretsmanager_secret_version" "paneldx_db" {
  count     = var.create_dedicated_rds ? 0 : 1
  secret_id = var.db_secret_id
}

locals {
  paneldx_db_secret = var.create_dedicated_rds ? {} : jsondecode(data.aws_secretsmanager_secret_version.paneldx_db[0].secret_string)

  dedicated_db_host = var.create_dedicated_rds ? aws_db_instance.inove4us[0].address : null
  dedicated_db_port = var.create_dedicated_rds ? tostring(aws_db_instance.inove4us[0].port) : null
  dedicated_db_name = var.create_dedicated_rds ? aws_db_instance.inove4us[0].db_name : null
  dedicated_db_user = var.create_dedicated_rds ? aws_db_instance.inove4us[0].username : null
  dedicated_db_pass = var.create_dedicated_rds ? random_password.rds_master[0].result : null

  db_host = coalesce(
    local.dedicated_db_host,
    try(local.paneldx_db_secret.host, null),
    var.secrets.db_host,
  )
  db_port = tostring(coalesce(
    local.dedicated_db_port,
    try(local.paneldx_db_secret.port, null),
    var.secrets.db_port,
  ))
  db_name = coalesce(
    local.dedicated_db_name,
    var.secrets.db_name != "" ? var.secrets.db_name : null,
    try(local.paneldx_db_secret.dbname, null),
    "inove4us",
  )
  db_user = coalesce(
    local.dedicated_db_user,
    try(local.paneldx_db_secret.username, null),
    var.secrets.db_user,
  )
  db_pass = coalesce(
    local.dedicated_db_pass,
    try(local.paneldx_db_secret.password, null),
    var.secrets.db_pass,
  )

  app_secret_key = var.secrets.secret_key != "" && var.secrets.secret_key != "CHANGE_ME_LONG_RANDOM_SECRET" ? var.secrets.secret_key : random_password.app_secret.result
}

resource "random_password" "app_secret" {
  length  = 48
  special = false
}
