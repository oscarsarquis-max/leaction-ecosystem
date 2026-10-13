# RDS PostgreSQL opcional do Monitor. Desligado por padrão.
# Não usa o RDS actionhub-prod. Não liga persistência canônica.

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

variable "task_role_name" {
  type        = string
  default     = ""
  description = "ECS task role that may read the database secret after Phase A."
}

variable "execution_role_name" {
  type        = string
  default     = ""
  description = "ECS execution role for injecting the secret in Phase B."
}

variable "alarm_topic_arn" {
  type    = string
  default = ""
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
  description = "Spider sandbox PostgreSQL - ECS tasks only"
  vpc_id      = var.vpc_id
  ingress {
    description     = "PostgreSQL from Spider ECS tasks"
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
  count                    = var.enabled ? 1 : 0
  name                     = "${var.name_prefix}/postgres"
  kms_key_id               = var.kms_key_arn
  recovery_window_in_days  = 7
  tags                     = var.tags
}

resource "aws_secretsmanager_secret_version" "db" {
  count     = var.enabled ? 1 : 0
  secret_id = aws_secretsmanager_secret.db[0].id
  secret_string = jsonencode({
    engine   = "postgres"
    username = "spider_runtime"
    password = random_password.db[0].result
    dbname   = "spider_orchestrator"
    port     = 5432
    host     = aws_db_instance.this[0].address
  })
}

resource "aws_db_parameter_group" "this" {
  count  = var.enabled ? 1 : 0
  name   = "${var.name_prefix}-pg16"
  family = "postgres16"
  parameter {
    name  = "timezone"
    value = "UTC"
  }
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }
  parameter {
    name         = "rds.force_ssl"
    value        = "1"
    apply_method = "pending-reboot"
  }
  tags = var.tags
}

resource "aws_cloudwatch_log_group" "postgresql" {
  count             = var.enabled ? 1 : 0
  name              = "/aws/rds/instance/${var.name_prefix}-pg/postgresql"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_db_instance" "this" {
  count                       = var.enabled ? 1 : 0
  identifier                  = "${var.name_prefix}-pg"
  engine                      = "postgres"
  engine_version              = "16.6"
  instance_class              = "db.t4g.micro"
  allocated_storage           = 20
  max_allocated_storage       = 50
  storage_type                = "gp3"
  db_name                     = "spider_orchestrator"
  username                    = "spider_runtime"
  password                    = random_password.db[0].result
  db_subnet_group_name        = aws_db_subnet_group.this[0].name
  vpc_security_group_ids      = [aws_security_group.db[0].id]
  parameter_group_name        = aws_db_parameter_group.this[0].name
  storage_encrypted           = true
  kms_key_id                  = var.kms_key_arn
  publicly_accessible         = false
  multi_az                    = false
  backup_retention_period     = 7
  backup_window               = "07:00-07:30"
  maintenance_window          = "sun:07:30-sun:08:00"
  deletion_protection         = true
  skip_final_snapshot         = false
  final_snapshot_identifier   = "${var.name_prefix}-final"
  copy_tags_to_snapshot       = true
  auto_minor_version_upgrade  = true
  apply_immediately           = false
  performance_insights_enabled = false
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  tags                        = var.tags
  depends_on                  = [aws_cloudwatch_log_group.postgresql]
}

resource "aws_iam_role_policy" "db_task" {
  count = var.enabled && var.task_role_name != "" ? 1 : 0
  name  = "${var.name_prefix}-db-secret-task"
  role  = var.task_role_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.db[0].arn]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [var.kms_key_arn]
      }
    ]
  })
}

resource "aws_iam_role_policy" "db_execution" {
  count = var.enabled && var.execution_role_name != "" ? 1 : 0
  name  = "${var.name_prefix}-db-secret-exec"
  role  = var.execution_role_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.db[0].arn]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [var.kms_key_arn]
      }
    ]
  })
}

resource "aws_cloudwatch_metric_alarm" "cpu" {
  count               = var.enabled && var.alarm_topic_arn != "" ? 1 : 0
  alarm_name          = "${var.name_prefix}-pg-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Spider sandbox Monitor PostgreSQL CPU"
  dimensions          = { DBInstanceIdentifier = aws_db_instance.this[0].id }
  alarm_actions       = [var.alarm_topic_arn]
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "storage" {
  count               = var.enabled && var.alarm_topic_arn != "" ? 1 : 0
  alarm_name          = "${var.name_prefix}-pg-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 2147483648
  alarm_description   = "Spider sandbox Monitor PostgreSQL free storage below 2 GiB"
  dimensions          = { DBInstanceIdentifier = aws_db_instance.this[0].id }
  alarm_actions       = [var.alarm_topic_arn]
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "connections" {
  count               = var.enabled && var.alarm_topic_arn != "" ? 1 : 0
  alarm_name          = "${var.name_prefix}-pg-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 40
  alarm_description   = "Spider sandbox Monitor PostgreSQL connection count"
  dimensions          = { DBInstanceIdentifier = aws_db_instance.this[0].id }
  alarm_actions       = [var.alarm_topic_arn]
  tags                = var.tags
}

output "endpoint" {
  value = var.enabled ? aws_db_instance.this[0].address : ""
}

output "secret_arn" {
  value = var.enabled ? aws_secretsmanager_secret.db[0].arn : ""
}

output "security_group_id" {
  value = var.enabled ? aws_security_group.db[0].id : ""
}

output "identifier" {
  value = var.enabled ? aws_db_instance.this[0].id : ""
}
