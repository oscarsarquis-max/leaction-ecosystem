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

variable "availability_zone" {
  type    = string
  default = "us-east-2a"
}

variable "blueprint_id" {
  type    = string
  default = "ubuntu_24_04"
}

variable "bundle_id" {
  type        = string
  default     = "small_3_0"
  description = "Lightsail 2 GB / ~US$12 com IPv4 (us-east-2)"
}

variable "api_hostname" {
  type    = string
  default = "api.homolog.qmind.com.br"
}

variable "app_hostname" {
  type    = string
  default = "app.homolog.qmind.com.br"
}

variable "pilot_api_hostname" {
  type        = string
  default     = "api.qmind.com.br"
  description = "API do piloto no domínio principal"
}

variable "pilot_app_hostname" {
  type        = string
  default     = "qmind.com.br"
  description = "App web do piloto (apex)"
}

variable "pilot_www_hostname" {
  type        = string
  default     = "www.qmind.com.br"
  description = "www do piloto (Caddy redireciona para apex)"
}

variable "route53_zone_id" {
  type        = string
  default     = "Z10252021E8KYKLG3TEOS"
  description = "Hosted zone qmind.com.br"
}

variable "admin_ssh_cidrs" {
  type        = list(string)
  default     = []
  description = "CIDRs para SSH:22. Vazio = SSH fechado (padrão do apply inicial)."

  validation {
    condition = alltrue([
      for c in var.admin_ssh_cidrs : c != "0.0.0.0/0" && c != "::/0"
    ])
    error_message = "admin_ssh_cidrs não pode incluir 0.0.0.0/0 nem ::/0. Use IP administrativo /32."
  }
}

variable "backup_prefix" {
  type    = string
  default = "pgdump/"
}

variable "backup_current_expiration_days" {
  type    = number
  default = 35
}

variable "backup_noncurrent_expiration_days" {
  type    = number
  default = 14
}

variable "evidence_noncurrent_expiration_days" {
  type        = number
  default     = 90
  description = "Expiração de versões não correntes de evidências (retenção homolog)"
}

variable "abort_multipart_days" {
  type    = number
  default = 7
}

variable "autosnapshot_time_utc" {
  type        = string
  default     = "06:00"
  description = "Horário UTC do AutoSnapshot Lightsail (HH:00)"
}

variable "alarm_sns_topic_arn" {
  type    = string
  default = null
}

variable "alarm_email" {
  type        = string
  default     = "gestao@leaction.com.br"
  description = "E-mail SNS + contato Lightsail (confirmar links pós-apply)"
}

variable "cognito_callback_urls" {
  type = list(string)
  default = [
    "https://app.homolog.qmind.com.br/auth/callback",
    "https://qmind.com.br/auth/callback",
  ]
}

variable "cognito_logout_urls" {
  type = list(string)
  default = [
    "https://app.homolog.qmind.com.br/",
    "https://qmind.com.br/",
  ]
}
