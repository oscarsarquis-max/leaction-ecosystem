terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  origin_host = trimprefix(trimsuffix(replace(var.public_origin, "https://", ""), "/"), "")
}

resource "aws_security_group" "alb" {
  name        = "${var.name_prefix}-alb"
  description = "ActionFinance public ingress"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTPS from the internet to this product only"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "service" {
  name        = "${var.name_prefix}-svc"
  description = "ActionFinance tasks reachable only from the product ALB"
  vpc_id      = var.vpc_id

  ingress {
    description     = "App port from ALB"
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb" "this" {
  name               = "${var.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
}

resource "aws_lb_target_group" "this" {
  name        = "${var.name_prefix}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = var.health_path
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.alb_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this.arn
  }
}

resource "aws_ecs_cluster" "this" {
  name = "${var.name_prefix}-cluster"
}

resource "aws_ecs_task_definition" "this" {
  family                   = var.name_prefix
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = var.name_prefix
      image     = var.image_uri
      essential = true
      portMappings = [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "SPRING_PROFILES_ACTIVE", value = "production" },
        { name = "ACTIONFINANCE_PUBLIC_ORIGIN", value = var.public_origin },
        { name = "ACTIONFINANCE_OIDC_REDIRECT_URI", value = "${var.public_origin}/login/oauth2/code/actionfinance" },
        { name = "ACTIONFINANCE_TRUST_FORWARDED_HEADERS", value = "false" },
        { name = "ACTIONFINANCE_FORWARD_HEADERS_STRATEGY", value = "none" },
        { name = "ACTIONFINANCE_BIND_ADDRESS", value = "0.0.0.0" }
      ]
      secrets = [
        { name = "ACTIONFINANCE_OIDC_ISSUER", valueFrom = "${var.oidc_secret_arn}:issuer::" },
        { name = "ACTIONFINANCE_OIDC_CLIENT_ID", valueFrom = "${var.oidc_secret_arn}:client_id::" },
        { name = "ACTIONFINANCE_OIDC_CLIENT_SECRET", valueFrom = "${var.oidc_secret_arn}:client_secret::" },
        { name = "ACTIONFINANCE_DATASOURCE_URL", valueFrom = "${var.database_secret_arn}:jdbc_url::" },
        { name = "ACTIONFINANCE_RUNTIME_USERNAME", valueFrom = "${var.database_secret_arn}:runtime_username::" },
        { name = "ACTIONFINANCE_RUNTIME_PASSWORD", valueFrom = "${var.database_secret_arn}:runtime_password::" },
        { name = "ACTIONFINANCE_MIGRATOR_USERNAME", valueFrom = "${var.database_secret_arn}:migrator_username::" },
        { name = "ACTIONFINANCE_MIGRATOR_PASSWORD", valueFrom = "${var.database_secret_arn}:migrator_password::" }
      ]
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://127.0.0.1:${var.container_port}${var.health_path} || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_iam_role" "execution" {
  name = "${var.name_prefix}-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task" {
  name = "${var.name_prefix}-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_ecs_service" "this" {
  name            = var.name_prefix
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.service.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.this.arn
    container_name   = var.name_prefix
    container_port   = var.container_port
  }
}

output "alb_dns_name" {
  value = aws_lb.this.dns_name
}

output "architecture" {
  value = "ALB TLS in ${var.aws_region} for ${local.origin_host}. No CloudFront. WAF is not a substitute for the IdP. Not applied."
}
