resource "aws_ecs_cluster" "this" {
  name = "${var.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "web" {
  count                    = local.serve ? 1 : 0
  family                   = "${var.name_prefix}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.web_execution.arn
  task_role_arn            = aws_iam_role.task.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = var.name_prefix
      image     = var.image_uri
      essential = true
      portMappings = [{
        containerPort = var.container_port
        protocol      = "tcp"
      }]
      environment = [
        { name = "SPRING_PROFILES_ACTIVE", value = "production" },
        { name = "ACTIONFINANCE_PUBLIC_ORIGIN", value = var.public_origin },
        { name = "ACTIONFINANCE_OIDC_REDIRECT_URI", value = "${var.public_origin}/login/oauth2/code/actionfinance" },
        { name = "ACTIONFINANCE_TRUST_FORWARDED_HEADERS", value = "false" },
        { name = "ACTIONFINANCE_FORWARD_HEADERS_STRATEGY", value = "none" },
        { name = "ACTIONFINANCE_BIND_ADDRESS", value = "0.0.0.0" },
        { name = "ACTIONFINANCE_FLYWAY_ENABLED", value = "false" },
        { name = "ACTIONFINANCE_READINESS_INCLUDE", value = "readinessState,db" }
      ]
      secrets = [
        { name = "ACTIONFINANCE_OIDC_ISSUER", valueFrom = "${aws_secretsmanager_secret.oidc.arn}:issuer::" },
        { name = "ACTIONFINANCE_OIDC_CLIENT_ID", valueFrom = "${aws_secretsmanager_secret.oidc.arn}:client_id::" },
        { name = "ACTIONFINANCE_OIDC_CLIENT_SECRET", valueFrom = "${aws_secretsmanager_secret.oidc.arn}:client_secret::" },
        { name = "ACTIONFINANCE_DATASOURCE_URL", valueFrom = "${aws_secretsmanager_secret.runtime.arn}:jdbc_url::" },
        { name = "ACTIONFINANCE_RUNTIME_USERNAME", valueFrom = "${aws_secretsmanager_secret.runtime.arn}:username::" },
        { name = "ACTIONFINANCE_RUNTIME_PASSWORD", valueFrom = "${aws_secretsmanager_secret.runtime.arn}:password::" }
      ]
      healthCheck = {
        command     = ["CMD-SHELL", "curl -fsS http://127.0.0.1:${var.container_port}${var.liveness_path} || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.web.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "web"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "migrate" {
  count                    = local.serve ? 1 : 0
  family                   = "${var.name_prefix}-migrate"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.migrate_execution.arn
  task_role_arn            = aws_iam_role.task.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = "${var.name_prefix}-migrate"
      image     = var.image_uri
      essential = true
      environment = [
        { name = "SPRING_PROFILES_ACTIVE", value = "production" },
        { name = "ACTIONFINANCE_PUBLIC_ORIGIN", value = var.public_origin },
        { name = "ACTIONFINANCE_OIDC_REDIRECT_URI", value = "${var.public_origin}/login/oauth2/code/actionfinance" },
        { name = "ACTIONFINANCE_TRUST_FORWARDED_HEADERS", value = "false" },
        { name = "ACTIONFINANCE_FORWARD_HEADERS_STRATEGY", value = "none" },
        { name = "ACTIONFINANCE_BIND_ADDRESS", value = "127.0.0.1" },
        { name = "ACTIONFINANCE_FLYWAY_ENABLED", value = "true" },
        { name = "ACTIONFINANCE_READINESS_INCLUDE", value = "readinessState,db,flywaySchema" }
      ]
      secrets = [
        { name = "ACTIONFINANCE_OIDC_ISSUER", valueFrom = "${aws_secretsmanager_secret.oidc.arn}:issuer::" },
        { name = "ACTIONFINANCE_OIDC_CLIENT_ID", valueFrom = "${aws_secretsmanager_secret.oidc.arn}:client_id::" },
        { name = "ACTIONFINANCE_OIDC_CLIENT_SECRET", valueFrom = "${aws_secretsmanager_secret.oidc.arn}:client_secret::" },
        { name = "ACTIONFINANCE_DATASOURCE_URL", valueFrom = "${aws_secretsmanager_secret.migrator.arn}:jdbc_url::" },
        { name = "ACTIONFINANCE_RUNTIME_USERNAME", valueFrom = "${aws_secretsmanager_secret.migrator.arn}:username::" },
        { name = "ACTIONFINANCE_RUNTIME_PASSWORD", valueFrom = "${aws_secretsmanager_secret.migrator.arn}:password::" },
        { name = "ACTIONFINANCE_MIGRATOR_USERNAME", valueFrom = "${aws_secretsmanager_secret.migrator.arn}:username::" },
        { name = "ACTIONFINANCE_MIGRATOR_PASSWORD", valueFrom = "${aws_secretsmanager_secret.migrator.arn}:password::" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.migrate.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "migrate"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "this" {
  count           = local.serve ? 1 : 0
  name            = var.name_prefix
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.web[0].arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.service.id]
    assign_public_ip = false
  }

  dynamic "load_balancer" {
    for_each = var.retire_dedicated_alb ? [] : [aws_lb_target_group.this[0].arn]
    content {
      target_group_arn = load_balancer.value
      container_name   = var.name_prefix
      container_port   = var.container_port
    }
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.shared.arn
    container_name   = var.name_prefix
    container_port   = var.container_port
  }

  depends_on = [aws_lb_listener_rule.shared_host]
}
