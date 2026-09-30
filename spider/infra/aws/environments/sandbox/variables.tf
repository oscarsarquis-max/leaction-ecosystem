variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "parent_zone_id" {
  type        = string
  description = "Hosted zone ID of actionhub.com.br. Only an NS record for spider is added."
}

variable "allowed_cidr_blocks" {
  type        = list(string)
  default     = []
  description = "Deprecated alias of sandbox_allowed_ipv4_cidrs. Prefer the named lists."
}

variable "sandbox_allowed_ipv4_cidrs" {
  type        = list(string)
  default     = []
  description = "Temporary operator IPv4 allowlist as /32 CIDRs. Empty keeps WAF default BLOCK."
}

variable "sandbox_allowed_ipv6_cidrs" {
  type        = list(string)
  default     = []
  description = "Optional operator IPv6 allowlist. Empty is the safe default."
}

variable "desired_count" {
  type        = number
  default     = 0
  description = "Keep 0 until a backend image exists in ECR. Memory persistence allows exactly one task."
}

variable "image_tag" {
  type        = string
  default     = "sandbox"
  description = "Immutable backend image tag or digest. Do not rely on latest."
}

variable "enable_database" {
  type    = bool
  default = false
}
