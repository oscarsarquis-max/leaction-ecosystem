# Snapshot diário Sponge (03:00 America/Sao_Paulo = 06:00 UTC).
# O deploy ECS também chama infra/scripts/ensure_snapshot_schedule.py para
# apontar o target à task definition vigente (evita tag pinada).

resource "aws_iam_role" "snapshot_events" {
  name = "${var.project}-${var.environment}-snapshot-events"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "snapshot_events" {
  name = "ecs-runtask-snapshot"
  role = aws_iam_role.snapshot_events.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecs:RunTask"]
        Resource = "arn:aws:ecs:${var.aws_region}:*:task-definition/${var.project}-${var.environment}*"
        Condition = {
          ArnEquals = {
            "ecs:cluster" = aws_ecs_cluster.inove4us.arn
          }
        }
      },
      {
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = [
          aws_iam_role.ecs_execution.arn,
          aws_iam_role.ecs_task.arn,
        ]
      }
    ]
  })
}

resource "aws_cloudwatch_event_rule" "conta_snapshot" {
  name                = "${var.project}-${var.environment}-conta-snapshot"
  description         = "Sponge: snapshot diário inove4us (03:00 America/Sao_Paulo)"
  schedule_expression = "cron(0 6 * * ? *)"
}

resource "aws_cloudwatch_event_target" "conta_snapshot" {
  rule      = aws_cloudwatch_event_rule.conta_snapshot.name
  target_id = "ecs-snapshot"
  arn       = aws_ecs_cluster.inove4us.arn
  role_arn  = aws_iam_role.snapshot_events.arn
  input = jsonencode({
    containerOverrides = [{
      name    = var.project
      command = ["python", "snapshot_conta.py"]
    }]
  })

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.inove4us.arn
    launch_type         = "FARGATE"
    network_configuration {
      subnets          = var.private_subnet_ids
      security_groups  = [aws_security_group.ecs_tasks.id]
      assign_public_ip = false
    }
  }
}
