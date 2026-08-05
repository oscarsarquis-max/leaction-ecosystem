#tfsec: ALB não existe; 80/443 públicos no host único são intencionais (ADR-010).

resource "aws_security_group" "app" {
  name        = "${var.name_prefix}-ec2"
  description = "QMind minimal-ec2 — HTTP/HTTPS públicos; Postgres sem exposição"
  vpc_id      = var.vpc_id

  #trivy:ignore:AVD-AWS-0107
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] #tfsec:ignore:aws-ec2-no-public-ingress-sgr
  }

  #trivy:ignore:AVD-AWS-0107
  ingress {
    description = "HTTP (ACME / redirect)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] #tfsec:ignore:aws-ec2-no-public-ingress-sgr
  }

  dynamic "ingress" {
    for_each = var.admin_ssh_cidr != "" ? [var.admin_ssh_cidr] : []
    content {
      description = "SSH admin only"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  #trivy:ignore:AVD-AWS-0104 # apt, Cognito, S3, ECR opcional, Let's Encrypt
  egress {
    description = "Outbound for updates, Cognito, S3, ACME"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] #tfsec:ignore:aws-ec2-no-public-egress-sgr
  }

  tags = {
    Name = "${var.name_prefix}-ec2"
  }
}
