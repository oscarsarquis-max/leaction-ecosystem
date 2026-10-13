variable "api_origin_hostname" {
  type        = string
  default     = ""
  description = "Hostname of the canonical API used as CloudFront origin for /v1/console/*."
}

variable "origin_verify_secret" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Shared secret sent only by CloudFront to the ALB origin. Not a user password."
}

variable "oidc_user_pool_id" {
  type    = string
  default = ""
}

variable "oidc_client_id" {
  type    = string
  default = ""
}

variable "oidc_domain" {
  type    = string
  default = ""
}

variable "oidc_issuer" {
  type    = string
  default = ""
}

variable "oidc_group" {
  type    = string
  default = "spider-sandbox-operators"
}

variable "monitor_ip_fallback_enabled" {
  type        = bool
  default     = true
  description = "Temporary IP allow rule while OIDC is proven. Not identity."
}

variable "edge_state_secret" {
  type      = string
  default   = ""
  sensitive = true
}

variable "enable_monitor_oidc" {
  type        = bool
  default     = true
  description = "Always-on for the sandbox Monitor. Kept as a static flag so count is known at plan time."
}

variable "oidc_published_version" {
  type        = string
  default     = "6"
  description = "Published Lambda@Edge version currently associated with CloudFront. Do not republish from this stack."
}

locals {
  oidc_published_arn = local.oidc_enabled ? "${aws_lambda_function.oidc[0].arn}:${var.oidc_published_version}" : null
  oidc_enabled     = var.enable_monitor_oidc
  api_origin_ready = var.api_origin_hostname != ""
  monitor_ip_rule  = var.monitor_ip_fallback_enabled && local.has_allowlist
  edge_source = replace(
    replace(
      replace(
        replace(
          replace(
            replace(
              replace(
                replace(file("${path.module}/edge/index.js"), "__POOL_ID__", var.oidc_user_pool_id),
                "__CLIENT_ID__",
                var.oidc_client_id
              ),
              "__ISSUER__",
              var.oidc_issuer
            ),
            "__COGNITO_DOMAIN__",
            var.oidc_domain
          ),
          "__MONITOR_HOST__",
          var.monitor_hostname
        ),
        "__APEX_HOST__",
        var.apex_hostname
      ),
      "__GROUP__",
      var.oidc_group
    ),
    "__STATE_SECRET__",
    var.edge_state_secret
  )
  edge_source_final = replace(local.edge_source, "__CREDENTIAL_REF__", "sandbox-operator")
}

data "archive_file" "oidc" {
  count       = local.oidc_enabled ? 1 : 0
  type        = "zip"
  output_path = "${path.module}/edge/oidc.zip"
  source {
    content  = local.edge_source_final
    filename = "index.js"
  }
}

data "aws_iam_policy_document" "edge_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com", "edgelambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "oidc" {
  count              = local.oidc_enabled ? 1 : 0
  name               = "${var.name_prefix}-monitor-oidc"
  assume_role_policy = data.aws_iam_policy_document.edge_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "oidc_logs" {
  count = local.oidc_enabled ? 1 : 0
  name  = "${var.name_prefix}-monitor-oidc-logs"
  role  = aws_iam_role.oidc[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = ["arn:aws:logs:*:${data.aws_caller_identity.current.account_id}:*"]
    }]
  })
}

resource "aws_cloudwatch_log_group" "oidc" {
  count             = local.oidc_enabled ? 1 : 0
  name              = "/aws/lambda/${var.name_prefix}-monitor-oidc"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_lambda_function" "oidc" {
  count            = local.oidc_enabled ? 1 : 0
  function_name    = "${var.name_prefix}-monitor-oidc"
  filename         = data.archive_file.oidc[0].output_path
  source_code_hash = data.archive_file.oidc[0].output_base64sha256
  role             = aws_iam_role.oidc[0].arn
  handler          = "index.handler"
  runtime          = "nodejs20.x"
  publish          = true
  timeout          = 5
  memory_size      = 128
  tags             = var.tags
  depends_on       = [aws_iam_role_policy.oidc_logs, aws_cloudwatch_log_group.oidc]
  lifecycle {
    # Publish path: infra/aws/scripts/prm009-inc001-patch-edge.py
    # This stack must not create version 7 from a local zip rebuild.
    ignore_changes = [filename, source_code_hash]
  }
}

resource "aws_lambda_permission" "oidc_replication" {
  count         = local.oidc_enabled ? 1 : 0
  statement_id  = "AllowCloudFrontReplicate"
  action        = "lambda:GetFunction"
  function_name = aws_lambda_function.oidc[0].function_name
  qualifier     = var.oidc_published_version
  principal     = "edgelambda.amazonaws.com"
  lifecycle {
    # State still has qualifier 1. Replacing it would destroy the leftover permission.
    # CloudFront uses version 6; replication permission for :6 already exists in AWS.
    ignore_changes = [qualifier]
  }
}

output "oidc_lambda_version_arn" {
  value = local.oidc_published_arn
}

output "monitor_ip_fallback_enabled" {
  value = local.monitor_ip_rule
}
