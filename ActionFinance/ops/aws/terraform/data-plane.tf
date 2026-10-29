resource "aws_ecr_repository" "this" {
  name                 = var.name_prefix
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration { scan_on_push = true }

  tags = { Product = "actionfinance" }
}

resource "aws_ecr_lifecycle_policy" "this" {
  repository = aws_ecr_repository.this.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_cloudwatch_log_group" "web" {
  name              = "/actionfinance/web"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "migrate" {
  name              = "/actionfinance/migrate"
  retention_in_days = var.log_retention_days
}

resource "aws_secretsmanager_secret" "oidc" {
  name                    = "actionfinance/oidc"
  description             = "OIDC issuer, client_id and client_secret. Values are put outside Terraform."
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "runtime" {
  name                    = "actionfinance/runtime"
  description             = "JDBC URL and runtime role only. Web execution role reads this secret."
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "migrator" {
  name                    = "actionfinance/migrator"
  description             = "JDBC URL and migrator role only. Web execution role cannot read this secret."
  recovery_window_in_days = 7
}

resource "aws_db_instance" "this" {
  identifier     = var.name_prefix
  engine         = "postgres"
  engine_version = var.postgres_engine_version
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = 50
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name                     = "actionfinance"
  username                    = "actionfinance_admin"
  manage_master_user_password = true
  port                        = 5432

  db_subnet_group_name       = aws_db_subnet_group.this.name
  vpc_security_group_ids     = [aws_security_group.db.id]
  publicly_accessible        = false
  multi_az                   = false
  deletion_protection        = true
  skip_final_snapshot        = false
  final_snapshot_identifier  = "${var.name_prefix}-final"
  backup_retention_period    = 7
  backup_window              = "07:00-08:00"
  maintenance_window         = "sun:08:00-sun:09:00"
  copy_tags_to_snapshot      = true
  auto_minor_version_upgrade = false

  tags = { Product = "actionfinance" }

  lifecycle {
    prevent_destroy = true
  }
}
