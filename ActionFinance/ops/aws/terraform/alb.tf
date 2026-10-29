resource "aws_lb" "this" {
  count              = var.retire_dedicated_alb ? 0 : 1
  name               = "${var.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb[0].id]
  subnets            = var.public_subnet_ids

  tags = { Product = "actionfinance" }
}

resource "aws_lb_target_group" "this" {
  count       = var.retire_dedicated_alb ? 0 : 1
  name        = "${var.name_prefix}-tg"
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

resource "aws_lb_listener" "https" {
  count             = var.retire_dedicated_alb ? 0 : 1
  load_balancer_arn = aws_lb.this[0].arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.this.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this[0].arn
  }
}

moved {
  from = aws_lb.this
  to   = aws_lb.this[0]
}

moved {
  from = aws_lb_target_group.this
  to   = aws_lb_target_group.this[0]
}

moved {
  from = aws_lb_listener.https
  to   = aws_lb_listener.https[0]
}
