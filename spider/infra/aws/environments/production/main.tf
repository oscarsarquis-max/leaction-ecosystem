locals {
  name_prefix = "spider-prod-canary"
  zone_name   = "spider.actionhub.com.br"
  zone_id     = "Z0546498APG2Z5CPDZEI"
  api_hostname     = "api.${local.zone_name}"
  monitor_hostname = "monitor.${local.zone_name}"
  company_id       = "624023a4-57e3-415c-b7d0-925ca1acd3b7"
  regional_certificate_arn = "arn:aws:acm:us-east-2:253137917703:certificate/ba5238d6-359a-4e96-a109-268e9646d370"
  cloudfront_certificate_arn = "arn:aws:acm:us-east-1:253137917703:certificate/2e8708d5-f9df-4244-9d30-dc8a9d7f27b9"
  ecr_repository_url       = "253137917703.dkr.ecr.us-east-2.amazonaws.com/spider-prod-canary-backend"
  image                    = "${local.ecr_repository_url}@${var.image_digest}"
  tags = {
    Project     = "spider"
    Environment = "production"
    ManagedBy   = "terraform"
    Domain      = local.zone_name
    Class       = "PRODUCTION"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ec2_managed_prefix_list" "cloudfront_origin" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

resource "random_password" "origin_verify" {
  length  = 48
  special = false
}

resource "random_password" "edge_state" {
  length  = 48
  special = false
}

resource "random_password" "actionfinance" {
  length  = 48
  special = false
}

resource "random_password" "pay_placeholder" {
  length  = 48
  special = false
}

module "network" {
  source         = "../../modules/network"
  name_prefix    = local.name_prefix
  vpc_cidr       = "10.82.0.0/16"
  occupied_cidrs = ["10.81.0.0/16", "10.0.0.0/16", "172.31.0.0/16"]
  azs            = slice(data.aws_availability_zones.available.names, 0, 2)
  enable_nat     = false
  tags           = local.tags
}

module "compute" {
  source                               = "../../modules/compute"
  name_prefix                          = local.name_prefix
  environment_name                     = "production"
  vpc_id                               = module.network.vpc_id
  public_subnet_ids                    = module.network.public_subnet_ids
  private_subnet_ids                   = module.network.private_subnet_ids
  acm_certificate_arn                  = local.regional_certificate_arn
  desired_count                        = 0
  assign_public_ip                     = true
  image_tag                            = "production"
  container_image                      = local.image
  spring_profile                       = "production"
  credential_env_name                  = "SPIDER_PRODUCTION_CREDENTIAL_REF"
  credential_ref                       = "production-operator"
  canonical_persistence_mode           = "jpa"
  monitor_persistence_mode             = "jpa"
  provider_mode                        = "ACTIVE"
  actionhub_pay_base_url               = "https://api.actionhub.com.br"
  database_required                    = true
  cors_origins                         = "https://${local.monitor_hostname}"
  log_group_name                       = "/spider/production/backend"
  kms_description                      = "Spider production application secrets"
  security_group_prefix                = "Spider production"
  deployment_maximum_percent           = 200
  deployment_minimum_healthy_percent   = 100
  allow_public_health                  = true
  manage_actionfinance_nat_ip_set      = true
  enable_execute_command               = true
  sandbox_allowed_ipv4_cidrs           = var.operator_ipv4_cidrs
  cloudfront_origin_prefix_list_id     = data.aws_ec2_managed_prefix_list.cloudfront_origin.id
  origin_verify_secret                 = random_password.origin_verify.result
  actionfinance_nat_ipv4_cidrs         = var.actionfinance_nat_ipv4_cidrs
  tags                                 = local.tags
}

module "identity" {
  source              = "../../modules/identity"
  name_prefix         = local.name_prefix
  monitor_hostname    = local.monitor_hostname
  operator_group_name        = "spider-production-operators"
  operator_group_description = "Operadores do Monitor Spider de produção"
  email_as_username          = false
  pool_name                  = "spider-prod-monitor"
  domain_prefix              = "spider-prod-monitor-253137917703"
  additional_monitor_hostnames = []
  tags                       = local.tags
}

module "frontend" {
  source                      = "../../modules/frontend"
  providers                   = { aws = aws.us_east_1 }
  name_prefix                 = local.name_prefix
  monitor_hostname            = local.monitor_hostname
  apex_hostname               = ""
  acm_certificate_arn         = local.cloudfront_certificate_arn
  sandbox_allowed_ipv4_cidrs  = var.operator_ipv4_cidrs
  api_origin_hostname         = local.api_hostname
  origin_verify_secret        = random_password.origin_verify.result
  oidc_user_pool_id           = module.identity.user_pool_id
  oidc_client_id              = module.identity.client_id
  oidc_domain                 = module.identity.hosted_ui_domain
  oidc_issuer                 = module.identity.issuer
  oidc_group                  = module.identity.operator_group_name
  credential_ref              = "production-operator"
  monitor_ip_fallback_enabled = true
  edge_state_secret           = random_password.edge_state.result
  oidc_published_version      = "3"
  tags                        = local.tags
}

module "database" {
  source                  = "../../modules/database"
  enabled                 = true
  name_prefix             = local.name_prefix
  vpc_id                  = module.network.vpc_id
  private_subnet_ids      = module.network.private_subnet_ids
  app_security_group_id   = module.compute.service_security_group_id
  kms_key_arn             = module.compute.kms_key_arn
  task_role_name          = module.compute.task_role_name
  execution_role_name     = module.compute.execution_role_name
  alarm_topic_arn         = module.observability.alarm_topic_arn
  alarm_prefix            = "Spider production PostgreSQL"
  multi_az                = false
  backup_retention_period = 7
  deletion_protection     = true
  tags                    = local.tags
}

module "observability" {
  source         = "../../modules/observability"
  name_prefix    = local.name_prefix
  alb_arn_suffix = module.compute.alb_arn_suffix
  tags           = local.tags
}

resource "aws_secretsmanager_secret" "actionfinance" {
  name       = "${local.name_prefix}/actionfinance"
  kms_key_id = module.compute.kms_key_arn
  tags       = local.tags
}

resource "aws_secretsmanager_secret_version" "actionfinance" {
  secret_id     = aws_secretsmanager_secret.actionfinance.id
  secret_string = random_password.actionfinance.result
}

resource "aws_secretsmanager_secret" "pay" {
  name       = "${local.name_prefix}/actionhub-pay"
  kms_key_id = module.compute.kms_key_arn
  tags       = local.tags
}

resource "aws_secretsmanager_secret_version" "pay" {
  secret_id     = aws_secretsmanager_secret.pay.id
  secret_string = random_password.pay_placeholder.result
  lifecycle {
    ignore_changes = [secret_string]
  }
  provisioner "local-exec" {
    command = "python scripts/install-pay-secret.py ${aws_secretsmanager_secret.pay.name}"
  }
}

resource "aws_iam_role_policy" "runtime_secrets" {
  name = "${local.name_prefix}-runtime-secrets"
  role = module.compute.execution_role_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        Resource = [
          aws_secretsmanager_secret.actionfinance.arn,
          aws_secretsmanager_secret.pay.arn,
          module.database.secret_arn
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [module.compute.kms_key_arn]
      }
    ]
  })
}

resource "aws_ecs_task_definition" "runtime" {
  family                   = "${local.name_prefix}-runtime"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = module.compute.execution_role_arn
  task_role_arn            = module.compute.task_role_arn
  container_definitions = jsonencode([{
    name      = "spider-backend"
    image     = local.image
    essential = true
    portMappings = [{
      containerPort = 8080
      hostPort      = 8080
      protocol      = "tcp"
    }]
    environment = [
      { name = "SPIDER_CANONICAL_PERSISTENCE_MODE", value = "jpa" },
      { name = "SPIDER_MONITOR_PERSISTENCE_MODE", value = "jpa" },
      { name = "SPIDER_CORS_ORIGINS", value = "https://${local.monitor_hostname}" },
      { name = "SPIDER_PRODUCTION_CREDENTIAL_REF", value = "production-operator" },
      { name = "SPRING_PROFILES_ACTIVE", value = "production" },
      { name = "SPIDER_ACTIONHUB_PAY_EDGE_URL", value = "https://api.actionhub.com.br" },
      { name = "SPIDER_ACTIONHUB_PAY_APP_ID", value = "lojadepaes" },
      { name = "SPIDER_MONITOR_ALLOWED_COMPANIES", value = local.company_id },
      { name = "SPIDER_MONITOR_JDBC_URL", value = "jdbc:postgresql://${module.database.endpoint}:5432/spider_orchestrator?ssl=true&sslmode=require" },
      { name = "SPIDER_CANONICAL_JDBC_URL", value = "jdbc:postgresql://${module.database.endpoint}:5432/spider_orchestrator?ssl=true&sslmode=require" }
    ]
    secrets = [
      { name = "SPIDER_JWT_SECRET", valueFrom = module.compute.jwt_secret_arn },
      { name = "SPIDER_MONITOR_JDBC_USERNAME", valueFrom = "${module.database.secret_arn}:username::" },
      { name = "SPIDER_MONITOR_JDBC_PASSWORD", valueFrom = "${module.database.secret_arn}:password::" },
      { name = "SPIDER_ACTIONFINANCE_APPLICATION_SECRET", valueFrom = aws_secretsmanager_secret.actionfinance.arn },
      { name = "SPIDER_ACTIONHUB_PAY_EDGE_SECRET", valueFrom = aws_secretsmanager_secret.pay.arn }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = module.compute.log_group_name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "runtime"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "wget -qO- http://127.0.0.1:8080/actuator/health/liveness || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 90
    }
    user = "1000"
  }])
  tags       = local.tags
  depends_on = [aws_iam_role_policy.runtime_secrets, aws_secretsmanager_secret_version.pay]
}

resource "aws_ecs_service" "runtime" {
  name                               = "${local.name_prefix}-runtime"
  cluster                            = module.compute.cluster_name
  task_definition                    = aws_ecs_task_definition.runtime.arn
  desired_count                      = 2
  launch_type                        = "FARGATE"
  enable_execute_command             = true
  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = module.network.public_subnet_ids
    security_groups  = [module.compute.service_security_group_id]
    assign_public_ip = true
  }
  load_balancer {
    target_group_arn = module.compute.target_group_arn
    container_name   = "spider-backend"
    container_port   = 8080
  }
  tags = local.tags
  depends_on = [
    aws_ecs_task_definition.runtime,
    module.database
  ]
  lifecycle {
    ignore_changes = [task_definition]
  }
}

# Canonical DNS (api, monitor) already exists in the zone and is not recreated here.
# Temporary canary hostnames are not part of production.
