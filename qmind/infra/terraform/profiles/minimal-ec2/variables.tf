variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "environment" {
  type    = string
  default = "homolog"
}

variable "name_prefix" {
  type    = string
  default = "qmind-homolog"
}

variable "vpc_id" {
  type        = string
  description = "VPC existente (sem NAT dedicado exigido)"
}

variable "public_subnet_id" {
  type        = string
  description = "Subnet pública com rota à Internet (EC2 + EIP)"
}

variable "instance_type" {
  type        = string
  default     = "t4g.small"
  description = "Preferir ARM (t4g.*) se imagens Docker forem multi-arch; senão t3.small"
}

variable "ami_architecture" {
  type        = string
  default     = "arm64"
  description = "arm64 (t4g) ou x86_64 (t3)"

  validation {
    condition     = contains(["arm64", "x86_64"], var.ami_architecture)
    error_message = "ami_architecture deve ser arm64 ou x86_64."
  }
}

variable "root_volume_gb" {
  type    = number
  default = 40
}

variable "domain_name" {
  type        = string
  description = "Hostname público (ex.: homolog.qmind.example.com) para Caddy/DNS"
}

variable "route53_zone_id" {
  type        = string
  default     = ""
  description = "Hosted zone para registro A → EIP; vazio = DNS manual"
}

variable "admin_ssh_cidr" {
  type        = string
  default     = ""
  description = "CIDR para SSH:22; vazio = sem SSH (usar SSM)"
}

variable "key_name" {
  type        = string
  default     = ""
  description = "Key pair EC2 opcional; preferir SSM sem key"
}

variable "enable_ssm" {
  type    = bool
  default = true
}

variable "cognito_callback_urls" {
  type = list(string)
}

variable "cognito_logout_urls" {
  type = list(string)
}

variable "alarm_sns_topic_arn" {
  type    = string
  default = null
}
