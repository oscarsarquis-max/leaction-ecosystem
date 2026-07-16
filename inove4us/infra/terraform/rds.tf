#############################################
# RDS PostgreSQL dedicado — inove4us
# Autônomo: não usa paneldx-database / LeAction_SysF
#############################################

resource "random_password" "rds_master" {
  count   = var.create_dedicated_rds ? 1 : 0
  length  = 32
  special = false
}

resource "aws_security_group" "rds" {
  count       = var.create_dedicated_rds ? 1 : 0
  name        = "${var.project}-${var.environment}-rds"
  description = "PostgreSQL dedicado inove4us"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Postgres from ECS tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  dynamic "ingress" {
    for_each = var.rds_bootstrap_cidr != "" ? [var.rds_bootstrap_cidr] : []
    content {
      description = "Temporary bootstrap from operator IP"
      from_port   = 5432
      to_port     = 5432
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project}-${var.environment}-rds"
  }
}

resource "aws_db_subnet_group" "inove4us" {
  count      = var.create_dedicated_rds ? 1 : 0
  name       = "${var.project}-${var.environment}"
  # Subnets públicas (IGW) permitem bootstrap com publicly_accessible;
  # com publicly_accessible=false o endpoint fica só na VPC (ECS alcança).
  subnet_ids = length(var.rds_subnet_ids) > 0 ? var.rds_subnet_ids : var.public_subnet_ids

  tags = {
    Name = "${var.project}-${var.environment}-db-subnets"
  }
}

resource "aws_db_instance" "inove4us" {
  count = var.create_dedicated_rds ? 1 : 0

  identifier     = "${var.project}-${var.environment}"
  engine         = "postgres"
  engine_version = var.rds_engine_version
  instance_class = var.rds_instance_class

  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "inove4us"
  username = var.rds_master_username
  password = random_password.rds_master[0].result
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.inove4us[0].name
  vpc_security_group_ids = [aws_security_group.rds[0].id]
  publicly_accessible    = var.rds_publicly_accessible
  multi_az               = var.rds_multi_az

  backup_retention_period = 7
  deletion_protection     = var.rds_deletion_protection
  skip_final_snapshot     = !var.rds_deletion_protection
  final_snapshot_identifier = var.rds_deletion_protection ? "${var.project}-${var.environment}-final" : null

  auto_minor_version_upgrade = true
  copy_tags_to_snapshot      = true

  tags = {
    Name = "${var.project}-${var.environment}-postgres"
  }
}

resource "aws_secretsmanager_secret" "inove4us_db" {
  count = var.create_dedicated_rds ? 1 : 0
  name  = "${var.project}/${var.environment}/db"

  tags = {
    Name = "${var.project}-db-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "inove4us_db" {
  count     = var.create_dedicated_rds ? 1 : 0
  secret_id = aws_secretsmanager_secret.inove4us_db[0].id
  secret_string = jsonencode({
    host     = aws_db_instance.inove4us[0].address
    port     = aws_db_instance.inove4us[0].port
    dbname   = aws_db_instance.inove4us[0].db_name
    username = aws_db_instance.inove4us[0].username
    password = random_password.rds_master[0].result
    engine   = "postgres"
  })
}
