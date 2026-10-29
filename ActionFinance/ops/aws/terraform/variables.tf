variable "aws_account_id" {
  type        = string
  description = "Target account. The provider caller identity must match this value on plan/apply."
  default     = "253137917703"
}

variable "aws_region" {
  type        = string
  description = "Compute, ALB, RDS, ECR and ACM regional certificate region."
  default     = "us-east-2"
}

variable "name_prefix" {
  type    = string
  default = "actionfinance"
}

variable "public_origin" {
  type        = string
  description = "Exact public origin, no path."
  default     = "https://actionfinance.actionhub.com.br"
}

variable "hosted_zone_id" {
  type        = string
  description = "Public hosted zone for actionhub.com.br. Used only for ActionFinance certificate validation and optional product alias."
  default     = "Z01698931CEOITJ7YYMYX"
}

variable "container_port" {
  type    = number
  default = 8091
}

variable "liveness_path" {
  type        = string
  description = "Process liveness. Used by the container healthCheck."
  default     = "/actuator/health/liveness"
}

variable "readiness_path" {
  type        = string
  description = "Readiness including database. Used by the ALB target group."
  default     = "/actuator/health/readiness"
}

variable "vpc_id" {
  type        = string
  description = "Existing PanelDX corporate VPC. Not the Spider sandbox VPC."
  default     = "vpc-017dc4cac16ba2c59"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnets for ECS tasks and RDS."
  default     = ["subnet-0a1da7a0765588962", "subnet-0693afdb3330b683a"]
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Public subnets for the ALB only."
  default     = ["subnet-04b323e5cea4d7273", "subnet-01fb021f890fe6e09"]
}

variable "image_uri" {
  type        = string
  description = "ECR image URI with @sha256 digest. Empty until the authorized push. Mutable tags are rejected."
  default     = ""

  validation {
    condition     = var.image_uri == "" || can(regex("@sha256:[0-9a-f]{64}$", var.image_uri))
    error_message = "image_uri must be empty or an ECR URI ending with @sha256:<64 hex>."
  }
}

variable "desired_count" {
  type        = number
  description = "Web tasks. Keep 0 until image digest, migrations and bootstrap are done."
  default     = 0
}

variable "enable_public_dns" {
  type        = bool
  description = "Create the actionfinance.actionhub.com.br alias. Leave false until TLS and OIDC are configured."
  default     = false
}

variable "shared_alb_name" {
  type        = string
  description = "Existing shared HTTP ingress ALB. Read via data source only; never imported into this state."
  default     = "paneldx-alb"
}

variable "shared_listener_rule_priority" {
  type        = number
  description = "Host rule priority on the shared HTTPS listener. Must be unused and numerically below the unscoped /api* rule."
  default     = 6

  validation {
    condition     = var.shared_listener_rule_priority >= 1 && var.shared_listener_rule_priority <= 50000
    error_message = "Listener rule priority must be a valid ALB priority."
  }
}

variable "ingress_alias" {
  type        = string
  description = "Which load balancer the public alias points to. dedicated during rollback window; shared after pre-DNS validation."
  default     = "dedicated"

  validation {
    condition     = contains(["dedicated", "shared"], var.ingress_alias)
    error_message = "ingress_alias must be dedicated or shared."
  }
}

variable "retire_dedicated_alb" {
  type        = bool
  description = "Destroy the unused dedicated ALB/listener/TG/SG after the shared path is validated. Irreversible without IaC rebuild."
  default     = false
}

variable "enable_cognito" {
  type        = bool
  description = "Dedicated Cognito user pool and confidential Authorization Code client."
  default     = true
}

variable "postgres_engine_version" {
  type        = string
  description = "RDS PostgreSQL version confirmed available in us-east-2 (17.5–17.11 on 30/09/2026). 17.9 matches actionhub-prod in this account without using that instance."
  default     = "17.9"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "log_retention_days" {
  type    = number
  default = 30
}
