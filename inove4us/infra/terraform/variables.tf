variable "aws_region" {
  type        = string
  description = "Região AWS (preferir a mesma do RDS PanelDX)"
  default     = "us-east-2"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "project" {
  type    = string
  default = "inove4us"
}

variable "domain_name" {
  type        = string
  description = "Domínio apex"
  default     = "inove4us.com.br"
}

variable "hosted_zone_id" {
  type        = string
  description = "Hosted Zone ID do Route 53 para inove4us.com.br (Z...)"
}

variable "vpc_id" {
  type        = string
  description = "VPC onde o serviço rodará (pode ser dedicada ou compartilhada)"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Subnets privadas para tasks Fargate"
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Subnets públicas para o ALB"
}

variable "container_image" {
  type        = string
  description = "URI da imagem no ECR (ex.: 123.dkr.ecr.us-east-1.amazonaws.com/inove4us:latest)"
}

variable "container_port" {
  type    = number
  default = 8080
}

variable "desired_count" {
  type    = number
  default = 2
}

variable "min_capacity" {
  type    = number
  default = 2
}

variable "max_capacity" {
  type    = number
  default = 20
}

variable "cpu" {
  type    = number
  default = 512
}

variable "memory" {
  type    = number
  default = 1024
}

variable "rds_security_group_id" {
  type        = string
  description = "SG do Postgres legado PanelDX (só usado se create_dedicated_rds=false)"
  default     = ""
}

variable "create_dedicated_rds" {
  type        = bool
  description = "Cria RDS PostgreSQL próprio do inove4us (recomendado)"
  default     = true
}

variable "rds_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "rds_engine_version" {
  type    = string
  default = "16.9"
}

variable "rds_allocated_storage" {
  type    = number
  default = 20
}

variable "rds_max_allocated_storage" {
  type    = number
  default = 100
}

variable "rds_master_username" {
  type    = string
  default = "inove4us_admin"
}

variable "rds_multi_az" {
  type    = bool
  default = false
}

variable "rds_deletion_protection" {
  type    = bool
  default = true
}

variable "rds_publicly_accessible" {
  type        = bool
  description = "true só para bootstrap inicial a partir do IP do operador"
  default     = false
}

variable "rds_bootstrap_cidr" {
  type        = string
  description = "CIDR /32 do operador para liberar 5432 temporariamente (vazio = sem regra)"
  default     = ""
}

variable "rds_subnet_ids" {
  type        = list(string)
  description = "Subnets do DB subnet group (default = public_subnet_ids)"
  default     = []
}

variable "certificate_arn" {
  type        = string
  description = "ACM certificate ARN para inove4us.com.br (+ www) na mesma região do ALB"
}

variable "db_secret_id" {
  type        = string
  description = "Secrets Manager legado PanelDX (só se create_dedicated_rds=false)"
  default     = "paneldx-db-credentials"
}

variable "secrets" {
  type = object({
    secret_key   = string
    db_host      = string
    db_port      = string
    db_name      = string
    db_user      = string
    db_pass      = string
    db_sslmode   = string
    email_sender = string
  })
  description = "Fallbacks. Com RDS dedicado, host/user/pass vêm do recurso aws_db_instance."
  sensitive   = true
  default = {
    secret_key   = ""
    db_host      = ""
    db_port      = "5432"
    db_name      = "inove4us"
    db_user      = "inove4us_admin"
    db_pass      = ""
    db_sslmode   = "require"
    email_sender = "noreply@inove4us.com.br"
  }
}
