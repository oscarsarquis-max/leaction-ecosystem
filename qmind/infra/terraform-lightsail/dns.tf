# Homolog (testes)
resource "aws_route53_record" "api" {
  zone_id = var.route53_zone_id
  name    = var.api_hostname
  type    = "A"
  ttl     = 60
  records = [aws_lightsail_static_ip.app.ip_address]
}

resource "aws_route53_record" "app" {
  zone_id = var.route53_zone_id
  name    = var.app_hostname
  type    = "A"
  ttl     = 60
  records = [aws_lightsail_static_ip.app.ip_address]
}

# Piloto (domínio principal) — mesmo IP Lightsail
resource "aws_route53_record" "pilot_api" {
  zone_id = var.route53_zone_id
  name    = var.pilot_api_hostname
  type    = "A"
  ttl     = 60
  records = [aws_lightsail_static_ip.app.ip_address]
}

resource "aws_route53_record" "pilot_app" {
  zone_id = var.route53_zone_id
  name    = var.pilot_app_hostname
  type    = "A"
  ttl     = 60
  records = [aws_lightsail_static_ip.app.ip_address]
}

resource "aws_route53_record" "pilot_www" {
  zone_id = var.route53_zone_id
  name    = var.pilot_www_hostname
  type    = "A"
  ttl     = 60
  records = [aws_lightsail_static_ip.app.ip_address]
}
