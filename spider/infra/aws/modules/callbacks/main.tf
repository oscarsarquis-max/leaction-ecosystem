# Ingress de callbacks preparado. Sem integração a rotas administrativas.
# O webhook legado /api/v1/webhooks/callback/{id} não é ingresso canônico publicável.

variable "name_prefix" {
  type = string
}

variable "callbacks_hostname" {
  type = string
}

variable "acm_certificate_arn" {
  type = string
}

variable "zone_id" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

resource "aws_apigatewayv2_api" "callbacks" {
  name          = "${var.name_prefix}-callbacks"
  protocol_type = "HTTP"
  description   = "Spider sandbox callback edge — no admin routes. Not wired until a publishable ingress exists."
  tags          = var.tags
}

resource "aws_apigatewayv2_stage" "sandbox" {
  api_id      = aws_apigatewayv2_api.callbacks.id
  name        = "sandbox"
  auto_deploy = true
  default_route_settings {
    throttling_burst_limit = 20
    throttling_rate_limit  = 10
  }
  tags = var.tags
}

resource "aws_apigatewayv2_domain_name" "callbacks" {
  domain_name = var.callbacks_hostname
  domain_name_configuration {
    certificate_arn = var.acm_certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
  tags = var.tags
}

resource "aws_apigatewayv2_api_mapping" "callbacks" {
  api_id      = aws_apigatewayv2_api.callbacks.id
  domain_name = aws_apigatewayv2_domain_name.callbacks.id
  stage       = aws_apigatewayv2_stage.sandbox.id
}

resource "aws_wafv2_web_acl" "callbacks" {
  name  = "${var.name_prefix}-callbacks"
  scope = "REGIONAL"
  default_action {
    block {}
  }
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.name_prefix}-callbacks"
    sampled_requests_enabled   = true
  }
  tags = var.tags
}

# HTTP API stage ARN is not accepted by WAF AssociateWebACL in this account.
# Isolation: no routes, no admin integration, WAF ACL retained for a future REST/ALB edge.

resource "aws_route53_record" "callbacks" {
  zone_id = var.zone_id
  name    = var.callbacks_hostname
  type    = "A"
  alias {
    name                   = aws_apigatewayv2_domain_name.callbacks.domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.callbacks.domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}

output "api_endpoint" {
  value = aws_apigatewayv2_api.callbacks.api_endpoint
}

output "custom_domain" {
  value = aws_apigatewayv2_domain_name.callbacks.domain_name
}
