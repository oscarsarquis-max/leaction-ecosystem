# RDS PostgreSQL opcional. Padrão desligado: sem Flyway no classpath e
# persistência canônica em memory. Não usar o RDS actionhub-prod.

variable "enabled" {
  type    = bool
  default = false
}

variable "name_prefix" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "app_security_group_id" {
  type = string
}

variable "kms_key_arn" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

resource "aws_db_subnet_group" "this" {
  count      = var.enabled ? 1 : 0
  name       = "${var.name_prefix}-db"
  subnet_ids = var.private_subnet_ids
  tags       = var.tags
}

resource "aws_security_group" "db" {
  count       = var.enabled ? 1 : 0
  name        = "${var.name_prefix}-db"
  description = "Spider sandbox PostgreSQL — app only"
  vpc_id      = var.vpc_id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.app_security_group_id]
  }
  tags = var.tags
}

resource "random_password" "db" {
  count   = var.enabled ? 1 : 0
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "db" {
  count      = var.enabled ? 1 : 0
  name       = "${var.name_prefix}/postgres"
  kms_key_id = var.kms_key_arn
  tags       = var.tags
}

resource "aws_secretsmanager_secret_version" "db" {
  count         = var.enabled ? 1 : 0
  secret_id     = aws_secretsmanager_secret.db[0].id
  secret_string = random_password.db[0].result
}

resource "aws_db_instance" "this" {
  count                      = var.enabled ? 1 : 0
  identifier                 = "${var.name_prefix}-pg"
  engine                     = "postgres"
  engine_version             = "16.6"
  instance_class             = "db.t4g.micro"
  allocated_storage          = 20
  db_name                    = "spider_orchestrator"
  username                   = "spider_runtime"
  password                   = random_password.db[0].result
  db_subnet_group_name       = aws_db_subnet_group.this[0].name
  vpc_security_group_ids     = [aws_security_group.db[0].id]
  storage_encrypted          = true
  kms_key_id                 = var.kms_key_arn
  publicly_accessible        = false
  multi_az                   = false
  backup_retention_period    = 7
  deletion_protection        = true
  skip_final_snapshot        = false
  final_snapshot_identifier  = "${var.name_prefix}-final"
  tags                       = var.tags
}

output "endpoint" {
  value = var.enabled ? aws_db_instance.this[0].address : ""
}
