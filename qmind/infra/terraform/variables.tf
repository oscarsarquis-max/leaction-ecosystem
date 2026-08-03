variable "aws_region" {
  type        = string
  description = "Região operacional QMind (ADR-009); ACM do ALB deve ser nesta região"
  default     = "us-east-2"
}

variable "environment" {
  type    = string
  default = "homolog"
}

variable "project" {
  type    = string
  default = "qmind"
}

variable "name_prefix" {
  type        = string
  description = "Prefixo de recursos (ex.: qmind-homolog)"
  default     = "qmind-homolog"
}

variable "vpc_id" {
  type        = string
  description = "VPC do ambiente homolog"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Subnets privadas (ECS tasks + RDS)"
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Subnets públicas (ALB)"
}

# --- DNS / TLS (sem secrets) ---

variable "certificate_arn" {
  type        = string
  description = "ARN de certificado ACM já validado em us-east-2; vazio = criar certificado DNS"
  default     = ""
}

variable "domain_name" {
  type        = string
  description = "Hostname principal (obrigatório se certificate_arn vazio; usado na criação ACM)"
  default     = ""

  validation {
    condition     = var.certificate_arn != "" || var.domain_name != ""
    error_message = "Informe certificate_arn (ACM us-east-2) ou domain_name para criar o certificado."
  }
}

variable "certificate_sans" {
  type        = list(string)
  description = "SANs adicionais quando Terraform cria o certificado"
  default     = []
}

variable "cors_origins" {
  type        = string
  description = "Origins CORS permitidos (não sensível)"
  default     = ""
}

# --- Compute ---

variable "container_port" {
  type    = number
  default = 8008
}

variable "cpu" {
  type    = number
  default = 512
}

variable "memory" {
  type    = number
  default = 1024
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "min_capacity" {
  type        = number
  description = "Autoscaling mínimo (conservador em homolog)"
  default     = 1
}

variable "max_capacity" {
  type        = number
  description = "Autoscaling máximo (conservador em homolog)"
  default     = 2
}

variable "autoscaling_cpu_target" {
  type    = number
  default = 70
}

variable "autoscaling_memory_target" {
  type    = number
  default = 75
}

variable "api_container_image" {
  type        = string
  description = "URI completa da imagem API (opcional). Se vazio, usa ECR + api_image_tag"
  default     = ""
}

variable "api_image_tag" {
  type        = string
  description = "Tag imutável no ECR da API (ex.: mvp-fullstack-v0 ou git sha)"
  default     = "mvp-fullstack-v0"
}

variable "alb_health_check_path" {
  type        = string
  description = "Path do health check do target group (liveness)"
  default     = "/health"
}

variable "container_readiness_path" {
  type        = string
  description = "Path de readiness no container healthCheck"
  default     = "/ready"
}

variable "alb_deletion_protection" {
  type    = bool
  default = false
}

variable "enable_ecs_exec" {
  type        = bool
  description = "ECS Exec (homolog pode desligar)"
  default     = false
}

variable "log_retention_days" {
  type    = number
  default = 30
}

# --- RDS ---

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "db_name" {
  type        = string
  description = "Database lógico Postgres"
  default     = "qmind"
}

variable "db_master_username" {
  type    = string
  default = "qmind_admin"
}

# --- Cognito URLs (não sensíveis) ---

variable "cognito_callback_urls" {
  type        = list(string)
  description = "URLs de callback do front homolog"
  default     = ["https://localhost/auth/callback"]
}

variable "cognito_logout_urls" {
  type    = list(string)
  default = ["https://localhost/"]
}

variable "evidence_retention_days" {
  type        = number
  description = "Lifecycle S3 opcional — 0 desliga"
  default     = 0
}

# --- Alarms ---

variable "alarm_sns_topic_arn" {
  type        = string
  description = "ARN SNS existente para alarmes; vazio = criar tópico"
  default     = ""
}

variable "alarm_alb_5xx_threshold" {
  type    = number
  default = 5
}

variable "alarm_alb_latency_p95_seconds" {
  type    = number
  default = 2
}

variable "alarm_ecs_cpu_threshold" {
  type    = number
  default = 85
}

variable "alarm_ecs_memory_threshold" {
  type    = number
  default = 85
}

variable "alarm_rds_cpu_threshold" {
  type    = number
  default = 80
}

variable "alarm_rds_free_storage_bytes" {
  type        = number
  description = "Alarme se free storage < este valor (default ~2 GiB)"
  default     = 2147483648
}

variable "alarm_rds_connections_threshold" {
  type    = number
  default = 80
}
