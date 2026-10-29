data "aws_iam_policy_document" "ecs_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "web_execution" {
  name               = "${var.name_prefix}-web-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role" "migrate_execution" {
  name               = "${var.name_prefix}-migrate-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role" "task" {
  name               = "${var.name_prefix}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "web_execution_base" {
  role       = aws_iam_role.web_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "migrate_execution_base" {
  role       = aws_iam_role.migrate_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "web_secrets" {
  name = "${var.name_prefix}-web-secrets"
  role = aws_iam_role.web_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadWebSecretsOnly"
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.oidc.arn, aws_secretsmanager_secret.runtime.arn]
    }]
  })
}

resource "aws_iam_role_policy" "migrate_secrets" {
  name = "${var.name_prefix}-migrate-secrets"
  role = aws_iam_role.migrate_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadMigratorSecretOnly"
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.migrator.arn, aws_secretsmanager_secret.oidc.arn]
    }]
  })
}
