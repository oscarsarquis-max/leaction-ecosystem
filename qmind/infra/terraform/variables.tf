variable "aws_region" {
  type        = string
  description = "Região operacional QMind (ADR-009)"
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
  description = "Subnets privadas (RDS / futuros tasks ECS)"
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Subnets públicas (futuro ALB)"
  default     = []
}

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
  description = "Transição para IA/Glacier opcional — 0 desliga lifecycle"
  default     = 0
}
