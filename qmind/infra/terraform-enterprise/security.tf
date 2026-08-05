# ALB → ECS → RDS
# tfsec: ALB público e egress amplo de tasks (NAT→ECR/S3/JWKS) são intencionais em homolog.

resource "aws_security_group" "alb" {
  name        = "${var.name_prefix}-alb"
  description = "QMind public ALB (HTTP redirect + HTTPS)"
  vpc_id      = var.vpc_id

  #trivy:ignore:AVD-AWS-0107 # HTTPS público no ALB homolog
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] #tfsec:ignore:aws-ec2-no-public-ingress-sgr
  }

  #trivy:ignore:AVD-AWS-0107 # HTTP→HTTPS redirect
  ingress {
    description = "HTTP redirect to HTTPS"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] #tfsec:ignore:aws-ec2-no-public-ingress-sgr
  }

  #trivy:ignore:AVD-AWS-0104
  egress {
    description = "Respostas aos clientes + path ao target group"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] #tfsec:ignore:aws-ec2-no-public-egress-sgr
  }

  tags = {
    Name = "${var.name_prefix}-alb"
  }
}

resource "aws_security_group" "ecs_tasks" {
  name        = "${var.name_prefix}-ecs-tasks"
  description = "QMind Fargate tasks — ingress only from ALB"
  vpc_id      = var.vpc_id

  ingress {
    description     = "App port from ALB"
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  #trivy:ignore:AVD-AWS-0104 # Egress via NAT: ECR, Secrets, S3, CW, Cognito JWKS, RDS
  egress {
    description = "RDS, ECR, Secrets, S3, CloudWatch, Cognito JWKS"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] #tfsec:ignore:aws-ec2-no-public-egress-sgr
  }

  tags = {
    Name = "${var.name_prefix}-ecs-tasks"
  }
}

resource "aws_security_group_rule" "rds_from_ecs" {
  type                     = "ingress"
  description              = "PostgreSQL from ECS tasks only"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.ecs_tasks.id
}
