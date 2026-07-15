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
  description = "SG do PostgreSQL compartilhado (LeAction_SysF) — receberá ingress 5432 do SG das tasks"
}

variable "certificate_arn" {
  type        = string
  description = "ACM certificate ARN para inove4us.com.br (+ www) na mesma região do ALB"
}

variable "db_secret_id" {
  type        = string
  description = "Secrets Manager com host/user/password do Postgres PanelDX"
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
  description = "Fallbacks / overrides. Senha do DB vem preferencialmente do Secrets Manager."
  sensitive   = true
  default = {
    secret_key   = ""
    db_host      = "paneldx-database.czqyam2auctn.us-east-2.rds.amazonaws.com"
    db_port      = "5432"
    db_name      = "LeAction_SysF"
    db_user      = "postgres"
    db_pass      = ""
    db_sslmode   = "require"
    email_sender = "noreply@inove4us.com.br"
  }
}
