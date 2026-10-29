# Associations on the existing shared ALB. The ALB itself is not imported or managed here.

data "aws_lb" "shared" {
  name = var.shared_alb_name
}

data "aws_lb_listener" "shared_https" {
  load_balancer_arn = data.aws_lb.shared.arn
  port              = 443
}

data "aws_security_group" "shared_alb" {
  id = one(data.aws_lb.shared.security_groups)
}

check "shared_alb_is_paneldx" {
  assert {
    condition     = data.aws_lb.shared.name == "paneldx-alb"
    error_message = "Shared ingress must remain paneldx-alb; refusing an unexpected load balancer."
  }
}

check "shared_alb_same_vpc" {
  assert {
    condition     = data.aws_lb.shared.vpc_id == var.vpc_id
    error_message = "Shared ALB is not in the ActionFinance VPC."
  }
}

check "retirement_requires_shared_alias" {
  assert {
    condition     = !var.retire_dedicated_alb || var.ingress_alias == "shared"
    error_message = "Cannot retire the dedicated ALB while the public alias still points at it."
  }
}

resource "aws_lb_target_group" "shared" {
  name        = "${var.name_prefix}-px-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = var.readiness_path
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = { Product = "actionfinance" }
}

resource "aws_lb_listener_certificate" "shared" {
  listener_arn    = data.aws_lb_listener.shared_https.arn
  certificate_arn = aws_acm_certificate_validation.this.certificate_arn
}

resource "aws_lb_listener_rule" "shared_host" {
  listener_arn = data.aws_lb_listener.shared_https.arn
  priority     = var.shared_listener_rule_priority

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.shared.arn
  }

  condition {
    host_header {
      values = [local.origin_host]
    }
  }
}

resource "aws_security_group_rule" "service_from_shared_alb" {
  type                     = "ingress"
  security_group_id        = aws_security_group.service.id
  from_port                = var.container_port
  to_port                  = var.container_port
  protocol                 = "tcp"
  source_security_group_id = data.aws_security_group.shared_alb.id
  description              = "App port from shared paneldx-alb"
}
