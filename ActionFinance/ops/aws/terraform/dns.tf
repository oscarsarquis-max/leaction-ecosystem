resource "aws_acm_certificate" "this" {
  domain_name       = local.origin_host
  validation_method = "DNS"

  lifecycle { create_before_destroy = true }

  tags = { Product = "actionfinance" }
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for option in aws_acm_certificate.this.domain_validation_options : option.domain_name => option
  }

  zone_id = var.hosted_zone_id
  name    = each.value.resource_record_name
  type    = each.value.resource_record_type
  records = [each.value.resource_record_value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "this" {
  certificate_arn         = aws_acm_certificate.this.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

locals {
  public_alias_dns  = var.ingress_alias == "shared" ? data.aws_lb.shared.dns_name : aws_lb.this[0].dns_name
  public_alias_zone = var.ingress_alias == "shared" ? data.aws_lb.shared.zone_id : aws_lb.this[0].zone_id
}

resource "aws_route53_record" "app" {
  count   = var.enable_public_dns ? 1 : 0
  zone_id = var.hosted_zone_id
  name    = local.origin_host
  type    = "A"

  alias {
    name                   = local.public_alias_dns
    zone_id                = local.public_alias_zone
    evaluate_target_health = true
  }
}
