resource "aws_route53_record" "apex" {
  zone_id = var.hosted_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.inove4us.dns_name
    zone_id                = aws_lb.inove4us.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "www" {
  zone_id = var.hosted_zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.inove4us.dns_name
    zone_id                = aws_lb.inove4us.zone_id
    evaluate_target_health = true
  }
}
