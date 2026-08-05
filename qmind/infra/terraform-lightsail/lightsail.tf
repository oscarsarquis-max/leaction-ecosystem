locals {
  # Metadados não sensíveis apenas — sem secrets/keys.
  # Sem indentação nas linhas: Lightsail/cloud-init ignora shebang com espaços
  # e roda com /bin/sh (dash), onde `set -o pipefail` falha.
  user_data = <<-EOT
#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl gnupg openssl unzip
curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
unzip -q /tmp/awscliv2.zip -d /tmp
/tmp/aws/install
rm -rf /tmp/aws /tmp/awscliv2.zip
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable --now docker
usermod -aG docker ubuntu || true
mkdir -p /opt/qmind/secrets /opt/qmind/bin
chmod 700 /opt/qmind/secrets
cat >/opt/qmind/INSTANCE_META.env <<META
QMIND_PROFILE=lightsail
QMIND_API_HOST=${var.api_hostname}
QMIND_APP_HOST=${var.app_hostname}
QMIND_PILOT_API_HOST=${var.pilot_api_hostname}
QMIND_PILOT_APP_HOST=${var.pilot_app_hostname}
QMIND_PILOT_WWW_HOST=${var.pilot_www_hostname}
QMIND_EVIDENCE_BUCKET=${aws_s3_bucket.evidence.id}
QMIND_BACKUP_BUCKET=${aws_s3_bucket.backups.id}
QMIND_BACKUP_PREFIX=${var.backup_prefix}
QMIND_AWS_REGION=${var.aws_region}
META
chmod 0644 /opt/qmind/INSTANCE_META.env
echo "Place IAM keys in /opt/qmind/secrets/*.env chmod 0600 — see CREDENTIALS.md" > /opt/qmind/secrets/README
chmod 0644 /opt/qmind/secrets/README
EOT
}

resource "aws_lightsail_instance" "app" {
  name              = "${var.name_prefix}-app"
  availability_zone = var.availability_zone
  blueprint_id      = var.blueprint_id
  bundle_id         = var.bundle_id
  user_data         = local.user_data

  add_on {
    type          = "AutoSnapshot"
    snapshot_time = var.autosnapshot_time_utc
    status        = "Enabled"
  }

  tags = {
    Name = "${var.name_prefix}-app"
  }

  # user_data só na 1ª criação — mudanças forçam replace e apagam o host provisionado.
  lifecycle {
    ignore_changes = [user_data]
  }
}

resource "aws_lightsail_static_ip" "app" {
  name = "${var.name_prefix}-ip"
}

resource "aws_lightsail_static_ip_attachment" "app" {
  static_ip_name = aws_lightsail_static_ip.app.name
  instance_name  = aws_lightsail_instance.app.name
}

# 80/443 públicos; SSH só com admin_ssh_cidrs (nunca 0.0.0.0/0 — validado na variável)
resource "aws_lightsail_instance_public_ports" "app" {
  instance_name = aws_lightsail_instance.app.name

  port_info {
    protocol  = "tcp"
    from_port = 80
    to_port   = 80
    cidrs     = ["0.0.0.0/0"]
  }

  port_info {
    protocol  = "tcp"
    from_port = 443
    to_port   = 443
    cidrs     = ["0.0.0.0/0"]
  }

  dynamic "port_info" {
    for_each = length(var.admin_ssh_cidrs) > 0 ? [1] : []
    content {
      protocol  = "tcp"
      from_port = 22
      to_port   = 22
      cidrs     = var.admin_ssh_cidrs
    }
  }

  depends_on = [aws_lightsail_static_ip_attachment.app]
}
