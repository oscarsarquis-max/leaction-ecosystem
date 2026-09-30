variable "aws_account_id" {
  type        = string
  description = "Observed corporate account used as documentation reference. Does not imply reuse of existing tasks."
  default     = "253137917703"
}

variable "aws_region" {
  type        = string
  description = "Compute, ALB and ACM regional certificate region."
  default     = "us-east-2"
}

variable "name_prefix" {
  type    = string
  default = "actionfinance"
}

variable "public_origin" {
  type        = string
  description = "Exact public origin, no path. Destination host is actionfinance.actionhub.com.br when activated."
  default     = "https://actionfinance.actionhub.com.br"
}

variable "container_port" {
  type    = number
  default = 8091
}

variable "health_path" {
  type    = string
  default = "/actuator/health/liveness"
}

variable "vpc_id" {
  type        = string
  description = "Existing VPC to reuse, or empty to create a dedicated VPC in a later apply."
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnets for ECS and RDS."
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Public subnets for the ALB only."
}

variable "alb_certificate_arn" {
  type        = string
  description = "ACM certificate in aws_region for the ALB listener. CloudFront is not in this architecture."
}

variable "image_uri" {
  type        = string
  description = "ECR image URI. Digest is recorded only after an authorized push."
}

variable "oidc_secret_arn" {
  type        = string
  description = "Secrets Manager ARN with issuer, client id and client secret. Not created here."
}

variable "database_secret_arn" {
  type        = string
  description = "Secrets Manager ARN with runtime and migrator passwords."
}

variable "desired_count" {
  type    = number
  default = 1
}
