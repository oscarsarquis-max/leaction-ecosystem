#tfsec:ignore:aws-sns-topic-encryption-use-cmk
resource "aws_sns_topic" "alarms" {
  count             = var.alarm_sns_topic_arn == null || var.alarm_sns_topic_arn == "" ? 1 : 0
  name              = "${var.name_prefix}-alarms"
  kms_master_key_id = "alias/aws/sns"
}

locals {
  alarm_actions = compact([
    var.alarm_sns_topic_arn != null && var.alarm_sns_topic_arn != ""
    ? var.alarm_sns_topic_arn
    : try(aws_sns_topic.alarms[0].arn, null)
  ])
}

resource "aws_cloudwatch_metric_alarm" "ec2_status_check" {
  alarm_name          = "${var.name_prefix}-ec2-status"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "breaching"
  alarm_description   = "EC2 status check failed"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    InstanceId = aws_instance.app.id
  }
}

resource "aws_cloudwatch_metric_alarm" "ec2_cpu" {
  alarm_name          = "${var.name_prefix}-ec2-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  treat_missing_data  = "notBreaching"
  alarm_description   = "EC2 CPU high"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    InstanceId = aws_instance.app.id
  }
}
