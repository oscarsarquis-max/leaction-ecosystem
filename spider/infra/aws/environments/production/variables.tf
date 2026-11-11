variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "image_digest" {
  type        = string
  description = "Image digest as sha256:<hex>. The task references repository@digest."
}

variable "operator_ipv4_cidrs" {
  type        = list(string)
  default     = []
  description = "Temporary operator CIDRs for the Monitor WAF. Empty keeps that surface closed."
}

variable "actionfinance_nat_ipv4_cidrs" {
  type    = list(string)
  default = ["3.143.92.115/32"]
}
