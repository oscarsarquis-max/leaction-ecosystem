variable "name_prefix" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "container_port" {
  type    = number
  default = 8080
}

variable "desired_count" {
  type    = number
  default = 0
}

variable "assign_public_ip" {
  type        = bool
  default     = true
  description = "true when NAT/EIP quota blocks private egress. Sandbox only."
}

variable "cpu" {
  type    = number
  default = 512
}

variable "memory" {
  type    = number
  default = 1024
}

variable "acm_certificate_arn" {
  type = string
}

variable "image_tag" {
  type    = string
  default = "sandbox"
}

variable "sandbox_allowed_ipv4_cidrs" {
  type        = list(string)
  default     = []
  description = "Temporary operator IPv4 /32 CIDRs for the public ALB. Empty leaves 443 closed."
}

variable "sandbox_allowed_ipv6_cidrs" {
  type        = list(string)
  default     = []
  description = "Optional operator IPv6 CIDRs for the public ALB."
}

variable "tags" {
  type    = map(string)
  default = {}
}

locals {
  has_ipv4_allow = length(var.sandbox_allowed_ipv4_cidrs) > 0
  has_ipv6_allow = length(var.sandbox_allowed_ipv6_cidrs) > 0
  has_allowlist  = local.has_ipv4_allow || local.has_ipv6_allow
}

resource "aws_ecr_repository" "backend" {
  name                 = "${var.name_prefix}-backend"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
  tags = var.tags
}

resource "aws_kms_key" "spider" {
  description         = "Spider sandbox application secrets"
  enable_key_rotation = true
  tags                = var.tags
}

resource "aws_kms_alias" "spider" {
  name          = "alias/${var.name_prefix}"
  target_key_id = aws_kms_key.spider.key_id
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/spider/sandbox/backend"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_security_group" "alb" {
  name        = "${var.name_prefix}-alb"
  description = "Spider sandbox ALB"
  vpc_id      = var.vpc_id
  dynamic "ingress" {
    for_each = local.has_ipv4_allow ? [1] : []
    content {
      description = "HTTPS from sandbox operator IPv4"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = var.sandbox_allowed_ipv4_cidrs
    }
  }
  dynamic "ingress" {
    for_each = local.has_ipv6_allow ? [1] : []
    content {
      description      = "HTTPS from sandbox operator IPv6"
      from_port        = 443
      to_port          = 443
      protocol         = "tcp"
      ipv6_cidr_blocks = var.sandbox_allowed_ipv6_cidrs
    }
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = var.tags
}

resource "aws_security_group" "service" {
  name        = "${var.name_prefix}-svc"
  description = "Spider sandbox ECS tasks"
  vpc_id      = var.vpc_id
  ingress {
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
  tags = var.tags
}

resource "aws_lb" "api" {
  name               = "${var.name_prefix}-alb"
  load_balancer_type = "application"
  internal           = false
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
  tags               = var.tags
}

resource "aws_lb_target_group" "api" {
  name        = "${var.name_prefix}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  deregistration_delay = 30
  health_check {
    path                = "/actuator/health/liveness"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
  tags = var.tags
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_ecs_cluster" "this" {
  name = var.name_prefix
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = var.tags
}

resource "aws_iam_role" "execution" {
  name = "${var.name_prefix}-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  name = "${var.name_prefix}-exec-secrets"
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.jwt.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [aws_kms_key.spider.arn]
      }
    ]
  })
}

resource "aws_iam_role" "task" {
  name = "${var.name_prefix}-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy" "task_secrets" {
  name = "${var.name_prefix}-secrets"
  role = aws_iam_role.task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.jwt.arn]
    }]
  })
}

resource "random_password" "jwt" {
  length  = 48
  special = false
}

resource "aws_secretsmanager_secret" "jwt" {
  name       = "${var.name_prefix}/jwt"
  kms_key_id = aws_kms_key.spider.arn
  tags       = var.tags
}

resource "aws_secretsmanager_secret_version" "jwt" {
  secret_id     = aws_secretsmanager_secret.jwt.id
  secret_string = random_password.jwt.result
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.name_prefix}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions = jsonencode([{
    name      = "spider-backend"
    image     = "${aws_ecr_repository.backend.repository_url}:${var.image_tag}"
    essential = true
    portMappings = [{
      containerPort = var.container_port
      protocol      = "tcp"
    }]
    environment = [
      { name = "SPRING_PROFILES_ACTIVE", value = "sandbox" },
      { name = "SPIDER_CORS_ORIGINS", value = "https://monitor.spider.actionhub.com.br,https://spider.actionhub.com.br" },
      { name = "SPIDER_SANDBOX_CREDENTIAL_REF", value = "sandbox-operator" },
      { name = "SPIDER_CANONICAL_PERSISTENCE_MODE", value = "memory" }
    ]
    secrets = [
      { name = "SPIDER_JWT_SECRET", valueFrom = aws_secretsmanager_secret.jwt.arn }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.backend.name
        awslogs-region        = data.aws_region.current.name
        awslogs-stream-prefix = "backend"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "wget -qO- http://127.0.0.1:8080/actuator/health/liveness || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
    user = "1000"
  }])
  tags = var.tags
}

data "aws_region" "current" {}

resource "aws_ecs_service" "backend" {
  name                               = "${var.name_prefix}-backend"
  cluster                            = aws_ecs_cluster.this.id
  task_definition                    = aws_ecs_task_definition.backend.arn
  desired_count                      = var.desired_count
  launch_type                        = "FARGATE"
  deployment_maximum_percent         = 100
  deployment_minimum_healthy_percent = 0
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = length(var.private_subnet_ids) > 0 && var.assign_public_ip == false ? var.private_subnet_ids : var.public_subnet_ids
    security_groups  = [aws_security_group.service.id]
    assign_public_ip = var.assign_public_ip
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "spider-backend"
    container_port   = var.container_port
  }
  tags       = var.tags
  depends_on = [aws_lb_listener.https]
}

resource "aws_wafv2_web_acl" "api" {
  name  = "${var.name_prefix}-api"
  scope = "REGIONAL"
  default_action {
    block {}
  }
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.name_prefix}-api"
    sampled_requests_enabled   = true
  }
  dynamic "rule" {
    for_each = local.has_allowlist ? [1] : []
    content {
      name     = "allow-sandbox-origins"
      priority = 1
      action {
        allow {}
      }
      statement {
        dynamic "ip_set_reference_statement" {
          for_each = local.has_ipv4_allow && !local.has_ipv6_allow ? [1] : []
          content {
            arn = aws_wafv2_ip_set.api_allow_ipv4[0].arn
          }
        }
        dynamic "ip_set_reference_statement" {
          for_each = !local.has_ipv4_allow && local.has_ipv6_allow ? [1] : []
          content {
            arn = aws_wafv2_ip_set.api_allow_ipv6[0].arn
          }
        }
        dynamic "or_statement" {
          for_each = local.has_ipv4_allow && local.has_ipv6_allow ? [1] : []
          content {
            statement {
              ip_set_reference_statement {
                arn = aws_wafv2_ip_set.api_allow_ipv4[0].arn
              }
            }
            statement {
              ip_set_reference_statement {
                arn = aws_wafv2_ip_set.api_allow_ipv6[0].arn
              }
            }
          }
        }
      }
      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${var.name_prefix}-api-allow"
        sampled_requests_enabled   = true
      }
    }
  }
  tags = var.tags
}

resource "aws_wafv2_ip_set" "api_allow_ipv4" {
  count              = local.has_ipv4_allow ? 1 : 0
  name               = "${var.name_prefix}-api-allow-v4"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.sandbox_allowed_ipv4_cidrs
  tags               = var.tags
}

resource "aws_wafv2_ip_set" "api_allow_ipv6" {
  count              = local.has_ipv6_allow ? 1 : 0
  name               = "${var.name_prefix}-api-allow-v6"
  scope              = "REGIONAL"
  ip_address_version = "IPV6"
  addresses          = var.sandbox_allowed_ipv6_cidrs
  tags               = var.tags
}

resource "aws_wafv2_web_acl_association" "api" {
  resource_arn = aws_lb.api.arn
  web_acl_arn  = aws_wafv2_web_acl.api.arn
}

output "alb_dns_name" {
  value = aws_lb.api.dns_name
}

output "alb_zone_id" {
  value = aws_lb.api.zone_id
}

output "ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "kms_key_arn" {
  value = aws_kms_key.spider.arn
}

output "service_security_group_id" {
  value = aws_security_group.service.id
}

output "alb_arn_suffix" {
  value = aws_lb.api.arn_suffix
}

output "service_name" {
  value = aws_ecs_service.backend.name
}

output "task_definition_arn" {
  value = aws_ecs_task_definition.backend.arn
}

output "target_group_arn" {
  value = aws_lb_target_group.api.arn
}
