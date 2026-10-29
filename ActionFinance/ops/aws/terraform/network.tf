resource "aws_security_group" "alb" {
  count       = var.retire_dedicated_alb ? 0 : 1
  name        = "${var.name_prefix}-alb"
  description = "ActionFinance public HTTPS ingress only"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTPS to this product ALB"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "To tasks in this VPC (targets are still limited by the service SG)"
    from_port   = var.container_port
    to_port     = var.container_port
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.this.cidr_block]
  }
}

resource "aws_security_group" "service" {
  name        = "${var.name_prefix}-svc"
  description = "ActionFinance tasks reachable only from the product ALB"
  vpc_id      = var.vpc_id

  dynamic "ingress" {
    for_each = var.retire_dedicated_alb ? [] : [1]
    content {
      description     = "App port from product ALB"
      from_port       = var.container_port
      to_port         = var.container_port
      protocol        = "tcp"
      security_groups = [aws_security_group.alb[0].id]
    }
  }

  lifecycle {
    ignore_changes = [ingress]
  }

  egress {
    description = "VPC endpoints, NAT instance and IdP HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "PostgreSQL in the private subnets of this VPC"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.128.0/20", "10.0.144.0/20"]
  }
}

resource "aws_security_group" "db" {
  name        = "${var.name_prefix}-db"
  description = "ActionFinance PostgreSQL from product tasks only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Postgres from ActionFinance tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.service.id]
  }
}

resource "aws_db_subnet_group" "this" {
  name        = "${var.name_prefix}-private"
  description = "ActionFinance private subnets. Does not manage actionhub-prod-private."
  subnet_ids  = var.private_subnet_ids
}

moved {
  from = aws_security_group.alb
  to   = aws_security_group.alb[0]
}
