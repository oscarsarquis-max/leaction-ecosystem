#tfsec:ignore:aws-sns-topic-encryption-use-cmk
resource "aws_sns_topic" "alarms" {
  count             = var.alarm_sns_topic_arn == null || var.alarm_sns_topic_arn == "" ? 1 : 0
  name              = "${var.name_prefix}-alarms"
  kms_master_key_id = "alias/aws/sns"
}

resource "aws_sns_topic_subscription" "alarms_email" {
  count     = var.alarm_sns_topic_arn == null || var.alarm_sns_topic_arn == "" ? 1 : 0
  topic_arn = aws_sns_topic.alarms[0].arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

locals {
  alarm_actions = compact([
    var.alarm_sns_topic_arn != null && var.alarm_sns_topic_arn != ""
    ? var.alarm_sns_topic_arn
    : try(aws_sns_topic.alarms[0].arn, null)
  ])
}

# Contato Lightsail (e-mail nativo dos alarmes AWS::Lightsail::Alarm). Confirmar link no e-mail.
resource "terraform_data" "lightsail_contact_email" {
  input = {
    email  = var.alarm_email
    region = var.aws_region
  }

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-NoProfile", "-Command"]
    command     = <<-EOT
      aws lightsail create-contact-method --region ${var.aws_region} --protocol Email --contact-endpoint '${var.alarm_email}'
      if ($LASTEXITCODE -ne 0) { Write-Host 'contact-method may already exist — OK'; exit 0 }
    EOT
  }
}

# Alarmes nativos Lightsail (monitored_resource_name) — não CloudWatch InstanceName
resource "aws_cloudformation_stack" "lightsail_alarms" {
  name = "${var.name_prefix}-ls-alarms"

  template_body = jsonencode({
    AWSTemplateFormatVersion = "2010-09-09"
    Description              = "QMind Lightsail native metric alarms"
    Resources = {
      CpuAlarm = {
        Type = "AWS::Lightsail::Alarm"
        Properties = {
          AlarmName             = "${var.name_prefix}-ls-cpu"
          MetricName            = "CPUUtilization"
          MonitoredResourceName = aws_lightsail_instance.app.name
          ComparisonOperator    = "GreaterThanThreshold"
          Threshold             = 85
          EvaluationPeriods     = 3
          DatapointsToAlarm     = 3
          TreatMissingData      = "notBreaching"
          ContactProtocols      = ["Email"]
          NotificationEnabled   = true
          NotificationTriggers  = ["ALARM", "OK"]
        }
      }
      StatusAlarm = {
        Type = "AWS::Lightsail::Alarm"
        Properties = {
          AlarmName             = "${var.name_prefix}-ls-status"
          MetricName            = "StatusCheckFailed"
          MonitoredResourceName = aws_lightsail_instance.app.name
          ComparisonOperator    = "GreaterThanThreshold"
          Threshold             = 0
          EvaluationPeriods     = 2
          DatapointsToAlarm     = 2
          TreatMissingData      = "breaching"
          ContactProtocols      = ["Email"]
          NotificationEnabled   = true
          NotificationTriggers  = ["ALARM", "OK"]
        }
      }
    }
  })

  depends_on = [
    aws_lightsail_instance.app,
    terraform_data.lightsail_contact_email,
  ]

  tags = {
    Name = "${var.name_prefix}-ls-alarms"
  }
}

# Backup: métrica custom QMind/Homolog → SNS. Ausência = alarme (até 1º backup OK).
resource "aws_cloudwatch_metric_alarm" "backup_failed" {
  alarm_name          = "${var.name_prefix}-backup-failed"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "BackupSuccess"
  namespace           = "QMind/Homolog"
  period              = 86400
  statistic           = "Maximum"
  threshold           = 1
  treat_missing_data  = "breaching"
  alarm_description   = "pg_dump diário ausente ou BackupSuccess < 1 — instalar cron; confirmar e-mail SNS"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    Environment = var.environment
  }
}
