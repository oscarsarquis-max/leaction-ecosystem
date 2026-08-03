resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.name_prefix}/api"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${var.name_prefix}/worker"
  retention_in_days = var.log_retention_days
}

resource "aws_ecs_cluster" "main" {
  name = var.name_prefix

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = var.name_prefix
  }
}

# --- IAM: execution role (agent) vs task role (app) ---

resource "aws_iam_role" "ecs_execution" {
  name = "${var.name_prefix}-ecs-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Minimal Secrets Manager read for injection at start (execution role only)
resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "${var.name_prefix}-exec-secrets"
  role = aws_iam_role.ecs_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadAppSecret"
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.app.arn]
    }]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "${var.name_prefix}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

# App runtime: evidence bucket only (no Secrets Manager — values injected as env)
resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "${var.name_prefix}-task-s3"
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EvidenceObjectRW"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:AbortMultipartUpload",
          "s3:ListBucketMultipartUploads",
          "s3:ListMultipartUploadParts",
        ]
        Resource = [
          aws_s3_bucket.evidence.arn,
          "${aws_s3_bucket.evidence.arn}/*",
        ]
      },
      {
        Sid      = "EvidenceListBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = [aws_s3_bucket.evidence.arn]
      }
    ]
  })
}

locals {
  api_image = (
    var.api_container_image != ""
    ? var.api_container_image
    : "${aws_ecr_repository.api.repository_url}:${var.api_image_tag}"
  )
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.name_prefix}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = local.api_image
    essential = true
    portMappings = [{
      containerPort = var.container_port
      protocol      = "tcp"
    }]
    environment = [
      { name = "ENVIRONMENT", value = var.environment },
      { name = "AUTH_MODE", value = "cognito" },
      { name = "STORAGE_BACKEND", value = "s3" },
      { name = "S3_BUCKET", value = aws_s3_bucket.evidence.bucket },
      { name = "S3_REGION", value = var.aws_region },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "AWS_DEFAULT_REGION", value = var.aws_region },
      { name = "COGNITO_REGION", value = var.aws_region },
      { name = "COGNITO_USER_POOL_ID", value = aws_cognito_user_pool.main.id },
      { name = "COGNITO_APP_CLIENT_ID", value = aws_cognito_user_pool_client.web.id },
      { name = "ALLOW_SIMULATED_SECURITY_PASS", value = "false" },
      { name = "PORT", value = tostring(var.container_port) },
      { name = "CORS_ORIGINS", value = var.cors_origins },
    ]
    # Sensitive DB URL: injected by execution role from Secrets Manager
    secrets = [
      {
        name      = "DATABASE_URL_APP"
        valueFrom = "${aws_secretsmanager_secret.app.arn}:DATABASE_URL_APP::"
      },
      {
        name      = "DATABASE_URL"
        valueFrom = "${aws_secretsmanager_secret.app.arn}:DATABASE_URL_APP::"
      },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.api.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "api"
      }
    }
    # Operational readiness: prefer /ready (DB); fall back path documented in DEPLOY
    healthCheck = {
      command = [
        "CMD-SHELL",
        "curl -fsS http://127.0.0.1:${var.container_port}${var.container_readiness_path} || curl -fsS http://127.0.0.1:${var.container_port}${var.alb_health_check_path} || exit 1",
      ]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "${var.name_prefix}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  platform_version = "1.4.0"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = var.container_port
  }

  # Rollback de deployment automático se health falhar
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  enable_execute_command = var.enable_ecs_exec

  depends_on = [
    aws_lb_listener.https,
    aws_iam_role_policy.ecs_execution_secrets,
  ]

  lifecycle {
    ignore_changes = [desired_count]
  }

  tags = {
    Name = "${var.name_prefix}-api"
  }
}
