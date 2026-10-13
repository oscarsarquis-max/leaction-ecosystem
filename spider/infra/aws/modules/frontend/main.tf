variable "name_prefix" {
  type = string
}

variable "monitor_hostname" {
  type = string
}

variable "apex_hostname" {
  type = string
}

variable "acm_certificate_arn" {
  type = string
}

variable "allowed_cidr_blocks" {
  type        = list(string)
  description = "Deprecated alias of sandbox_allowed_ipv4_cidrs."
  default     = []
}

variable "sandbox_allowed_ipv4_cidrs" {
  type        = list(string)
  description = "Temporary operator IPv4 /32 CIDRs. Empty keeps WAF default BLOCK."
  default     = []
}

variable "sandbox_allowed_ipv6_cidrs" {
  type        = list(string)
  description = "Optional operator IPv6 CIDRs. Empty is the safe default."
  default     = []
}

locals {
  allowed_ipv4_cidrs = distinct(concat(var.sandbox_allowed_ipv4_cidrs, var.allowed_cidr_blocks))
  allowed_ipv6_cidrs = var.sandbox_allowed_ipv6_cidrs
  has_ipv4_allow     = length(local.allowed_ipv4_cidrs) > 0
  has_ipv6_allow     = length(local.allowed_ipv6_cidrs) > 0
  has_allowlist      = local.has_ipv4_allow || local.has_ipv6_allow
}

variable "tags" {
  type    = map(string)
  default = {}
}

resource "aws_s3_bucket" "web" {
  bucket = "${var.name_prefix}-monitor-web"
  tags   = var.tags
}

resource "aws_s3_bucket_public_access_block" "web" {
  bucket                  = aws_s3_bucket.web.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "web" {
  bucket = aws_s3_bucket.web.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_cloudfront_origin_access_control" "web" {
  name                              = "${var.name_prefix}-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_function" "apex_redirect" {
  name    = "${var.name_prefix}-apex-redirect"
  runtime = "cloudfront-js-2.0"
  comment = "Redirect apex Spider host to Monitor"
  publish = true
  code    = <<-JS
    function handler(event) {
      var request = event.request;
      var host = request.headers.host.value;
      if (host === "${var.apex_hostname}") {
        return {
          statusCode: 301,
          statusDescription: "Moved Permanently",
          headers: {
            location: { value: "https://${var.monitor_hostname}" + request.uri }
          }
        };
      }
      var uri = request.uri;
      if (uri === "/") {
        request.uri = "/index.html";
        return request;
      }
      if (uri.indexOf(".") === -1) {
        request.uri = "/index.html";
      }
      return request;
    }
  JS
}

resource "aws_wafv2_web_acl" "monitor" {
  name  = "${var.name_prefix}-monitor"
  scope = "CLOUDFRONT"
  default_action {
    block {}
  }
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.name_prefix}-monitor"
    sampled_requests_enabled   = true
  }

  rule {
    name     = "aws-ip-reputation"
    priority = 0
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
        version     = null
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name_prefix}-ip-rep"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "aws-common"
    priority = 1
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
        version     = null
        rule_action_override {
          name = "SizeRestrictions_COOKIE"
          action_to_use {
            count {}
          }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name_prefix}-common"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "aws-known-bad-inputs"
    priority = 2
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
        version     = null
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name_prefix}-bad-inputs"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "rate-limit"
    priority = 3
    action {
      block {}
    }
    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name_prefix}-rate"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "allow-monitor-reads"
    priority = 10
    action {
      allow {}
    }
    statement {
      or_statement {
        statement {
          byte_match_statement {
            search_string         = "GET"
            positional_constraint = "EXACTLY"
            field_to_match {
              method {}
            }
            text_transformation {
              priority = 0
              type     = "NONE"
            }
          }
        }
        statement {
          byte_match_statement {
            search_string         = "HEAD"
            positional_constraint = "EXACTLY"
            field_to_match {
              method {}
            }
            text_transformation {
              priority = 0
              type     = "NONE"
            }
          }
        }
        statement {
          byte_match_statement {
            search_string         = "OPTIONS"
            positional_constraint = "EXACTLY"
            field_to_match {
              method {}
            }
            text_transformation {
              priority = 0
              type     = "NONE"
            }
          }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name_prefix}-reads"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "allow-console-writes"
    priority = 11
    action {
      allow {}
    }
    statement {
      and_statement {
        statement {
          or_statement {
            statement {
              byte_match_statement {
                search_string         = "/v1/console"
                positional_constraint = "STARTS_WITH"
                field_to_match {
                  uri_path {}
                }
                text_transformation {
                  priority = 0
                  type     = "NONE"
                }
              }
            }
            statement {
              byte_match_statement {
                search_string         = "/v1/canonical"
                positional_constraint = "STARTS_WITH"
                field_to_match {
                  uri_path {}
                }
                text_transformation {
                  priority = 0
                  type     = "NONE"
                }
              }
            }
          }
        }
        statement {
          or_statement {
            statement {
              byte_match_statement {
                search_string         = "POST"
                positional_constraint = "EXACTLY"
                field_to_match {
                  method {}
                }
                text_transformation {
                  priority = 0
                  type     = "NONE"
                }
              }
            }
            statement {
              byte_match_statement {
                search_string         = "PUT"
                positional_constraint = "EXACTLY"
                field_to_match {
                  method {}
                }
                text_transformation {
                  priority = 0
                  type     = "NONE"
                }
              }
            }
            statement {
              byte_match_statement {
                search_string         = "PATCH"
                positional_constraint = "EXACTLY"
                field_to_match {
                  method {}
                }
                text_transformation {
                  priority = 0
                  type     = "NONE"
                }
              }
            }
            statement {
              byte_match_statement {
                search_string         = "DELETE"
                positional_constraint = "EXACTLY"
                field_to_match {
                  method {}
                }
                text_transformation {
                  priority = 0
                  type     = "NONE"
                }
              }
            }
          }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name_prefix}-monitor-console-canonical-write"
      sampled_requests_enabled   = true
    }
  }

  dynamic "rule" {
    for_each = local.monitor_ip_rule ? [1] : []
    content {
      name     = "allow-sandbox-origins"
      priority = 20
      action {
        allow {}
      }
      statement {
        dynamic "ip_set_reference_statement" {
          for_each = local.has_ipv4_allow && !local.has_ipv6_allow ? [1] : []
          content {
            arn = aws_wafv2_ip_set.allow_ipv4[0].arn
          }
        }
        dynamic "ip_set_reference_statement" {
          for_each = !local.has_ipv4_allow && local.has_ipv6_allow ? [1] : []
          content {
            arn = aws_wafv2_ip_set.allow_ipv6[0].arn
          }
        }
        dynamic "or_statement" {
          for_each = local.has_ipv4_allow && local.has_ipv6_allow ? [1] : []
          content {
            statement {
              ip_set_reference_statement {
                arn = aws_wafv2_ip_set.allow_ipv4[0].arn
              }
            }
            statement {
              ip_set_reference_statement {
                arn = aws_wafv2_ip_set.allow_ipv6[0].arn
              }
            }
          }
        }
      }
      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${var.name_prefix}-allow"
        sampled_requests_enabled   = true
      }
    }
  }

  tags = var.tags
}

resource "aws_wafv2_ip_set" "allow_ipv4" {
  count              = local.has_ipv4_allow ? 1 : 0
  name               = "${var.name_prefix}-monitor-allow-v4"
  scope              = "CLOUDFRONT"
  ip_address_version = "IPV4"
  addresses          = local.allowed_ipv4_cidrs
  tags               = var.tags
}

resource "aws_wafv2_ip_set" "allow_ipv6" {
  count              = local.has_ipv6_allow ? 1 : 0
  name               = "${var.name_prefix}-monitor-allow-v6"
  scope              = "CLOUDFRONT"
  ip_address_version = "IPV6"
  addresses          = local.allowed_ipv6_cidrs
  tags               = var.tags
}

resource "aws_cloudwatch_log_group" "waf" {
  name              = "aws-waf-logs-${var.name_prefix}-monitor"
  retention_in_days = 30
  tags              = var.tags
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "waf_logs" {
  statement {
    sid    = "AWSLogDeliveryWrite"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["delivery.logs.amazonaws.com"]
    }
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.waf.arn}:*"]
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_cloudwatch_log_resource_policy" "waf" {
  policy_name     = "${var.name_prefix}-waf-logs"
  policy_document = data.aws_iam_policy_document.waf_logs.json
}

resource "aws_wafv2_web_acl_logging_configuration" "monitor" {
  resource_arn            = aws_wafv2_web_acl.monitor.arn
  log_destination_configs = [aws_cloudwatch_log_group.waf.arn]
  redacted_fields {
    single_header {
      name = "authorization"
    }
  }
  redacted_fields {
    single_header {
      name = "cookie"
    }
  }
  redacted_fields {
    single_header {
      name = "x-spider-credential-ref"
    }
  }
  depends_on = [aws_cloudwatch_log_resource_policy.waf]
}

resource "aws_cloudfront_response_headers_policy" "security" {
  name = "${var.name_prefix}-security-headers"
  security_headers_config {
    content_security_policy {
      content_security_policy = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
      override                = true
    }
    content_type_options {
      override = true
    }
    frame_options {
      frame_option = "DENY"
      override     = true
    }
    referrer_policy {
      referrer_policy = "same-origin"
      override        = true
    }
    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      override                   = true
    }
    xss_protection {
      protection = true
      mode_block = true
      override   = true
    }
  }
}

resource "aws_cloudfront_distribution" "monitor" {
  enabled             = true
  is_ipv6_enabled     = false
  comment             = "Spider sandbox Monitor — not production"
  default_root_object = "index.html"
  aliases             = [var.monitor_hostname, var.apex_hostname]
  web_acl_id          = aws_wafv2_web_acl.monitor.arn
  price_class         = "PriceClass_100"

  origin {
    domain_name              = aws_s3_bucket.web.bucket_regional_domain_name
    origin_id                = "s3-monitor"
    origin_access_control_id = aws_cloudfront_origin_access_control.web.id
  }

  dynamic "origin" {
    for_each = local.api_origin_ready ? [1] : []
    content {
      domain_name = var.api_origin_hostname
      origin_id   = "alb-console"
      custom_origin_config {
        http_port              = 80
        https_port             = 443
        origin_protocol_policy = "https-only"
        origin_ssl_protocols   = ["TLSv1.2"]
      }
      custom_header {
        name  = "x-spider-origin-secret"
        value = var.origin_verify_secret
      }
    }
  }

  default_cache_behavior {
    target_origin_id           = "s3-monitor"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad" # CachingDisabled — index.html / SPA
    response_headers_policy_id = "21888ced-287c-4e17-9680-fcb681851949" # CORS-With-Preflight (live)
    dynamic "function_association" {
      for_each = local.oidc_enabled ? [] : [1]
      content {
        event_type   = "viewer-request"
        function_arn = aws_cloudfront_function.apex_redirect.arn
      }
    }
    dynamic "lambda_function_association" {
      for_each = local.oidc_enabled ? [1] : []
      content {
        event_type   = "viewer-request"
        lambda_arn   = local.oidc_published_arn
        include_body = false
      }
    }
  }

  dynamic "ordered_cache_behavior" {
    for_each = local.api_origin_ready ? [1] : []
    content {
      path_pattern               = "/v1/console/*"
      target_origin_id           = "alb-console"
      viewer_protocol_policy     = "redirect-to-https"
      allowed_methods            = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      cached_methods             = ["GET", "HEAD"]
      compress                   = true
      cache_policy_id            = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
      origin_request_policy_id   = "b689b0a8-53d0-40ab-baf2-68738e2966ac" # AllViewerExceptHostHeader
      response_headers_policy_id = "21888ced-287c-4e17-9680-fcb681851949"
      dynamic "lambda_function_association" {
        for_each = local.oidc_enabled ? [1] : []
        content {
          event_type   = "viewer-request"
          lambda_arn   = local.oidc_published_arn
          include_body = false
        }
      }
    }
  }

  ordered_cache_behavior {
    path_pattern               = "/assets/*"
    target_origin_id           = "s3-monitor"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = "658327ea-f89d-4fab-a63d-7e88639e58f6" # CachingOptimized — hashed assets
    response_headers_policy_id = "21888ced-287c-4e17-9680-fcb681851949"
    dynamic "lambda_function_association" {
      for_each = local.oidc_enabled ? [1] : []
      content {
        event_type   = "viewer-request"
        lambda_arn   = local.oidc_published_arn
        include_body = false
      }
    }
  }

  dynamic "ordered_cache_behavior" {
    for_each = local.api_origin_ready ? [1] : []
    content {
      path_pattern               = "/v1/canonical/*"
      target_origin_id           = "alb-console"
      viewer_protocol_policy     = "redirect-to-https"
      allowed_methods            = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      cached_methods             = ["GET", "HEAD"]
      compress                   = true
      cache_policy_id            = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
      origin_request_policy_id   = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
      response_headers_policy_id = "21888ced-287c-4e17-9680-fcb681851949"
      dynamic "lambda_function_association" {
        for_each = local.oidc_enabled ? [1] : []
        content {
          event_type   = "viewer-request"
          lambda_arn   = local.oidc_published_arn
          include_body = false
        }
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = var.acm_certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = var.tags
  lifecycle {
    # Cosmetic only: em-dash in comment has drifted across editors. Behaviors are coded.
    ignore_changes = [comment]
  }
}

data "aws_iam_policy_document" "bucket" {
  statement {
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.web.arn}/*"]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.monitor.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "web" {
  bucket = aws_s3_bucket.web.id
  policy = data.aws_iam_policy_document.bucket.json
}

output "bucket_name" {
  value = aws_s3_bucket.web.bucket
}

output "distribution_id" {
  value = aws_cloudfront_distribution.monitor.id
}

output "distribution_domain" {
  value = aws_cloudfront_distribution.monitor.domain_name
}

output "distribution_hosted_zone_id" {
  value = aws_cloudfront_distribution.monitor.hosted_zone_id
}
