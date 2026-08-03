# ACM must be in the same region as the ALB (us-east-2).

resource "aws_acm_certificate" "alb" {
  count = var.certificate_arn == "" ? 1 : 0

  domain_name               = var.domain_name
  subject_alternative_names = var.certificate_sans
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

locals {
  acm_certificate_arn = var.certificate_arn != "" ? var.certificate_arn : aws_acm_certificate.alb[0].arn
}
