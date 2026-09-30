variable "zone_name" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

resource "aws_route53_zone" "spider" {
  name    = var.zone_name
  comment = "Delegated public zone for Spider sandbox. Not ActionHub apex."
  tags    = var.tags
}

output "zone_id" {
  value = aws_route53_zone.spider.zone_id
}

output "name_servers" {
  value = aws_route53_zone.spider.name_servers
}

output "zone_name" {
  value = aws_route53_zone.spider.name
}
