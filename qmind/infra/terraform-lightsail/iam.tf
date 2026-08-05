# Credenciais: criar access keys FORA do Terraform (CLI/console) após apply.
# Nunca colocar keys em user-data, outputs ou state. Ver CREDENTIALS.md.

# --- App runtime: somente bucket de evidências (inclui DeleteObject para descarte de domínio) ---

resource "aws_iam_user" "app_evidence" {
  name = "${var.name_prefix}-app-evidence"
  path = "/qmind/"
  tags = {
    Purpose = "qmind-app-evidence-only"
  }
}

#tfsec:ignore:aws-iam-no-policy-wildcards
resource "aws_iam_user_policy" "app_evidence" {
  name = "${var.name_prefix}-app-evidence"
  user = aws_iam_user.app_evidence.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EvidenceObjects"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:AbortMultipartUpload",
          "s3:ListMultipartUploadParts",
        ]
        Resource = ["${aws_s3_bucket.evidence.arn}/*"]
      },
      {
        Sid      = "EvidenceList"
        Effect   = "Allow"
        Action   = ["s3:ListBucket", "s3:ListBucketMultipartUploads"]
        Resource = [aws_s3_bucket.evidence.arn]
      },
      {
        Sid    = "DenyAllBackups"
        Effect = "Deny"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.backups.arn,
          "${aws_s3_bucket.backups.arn}/*",
        ]
      },
    ]
  })
}

# --- Backup job no host: PutObject no prefixo; sem Get/Delete (restore = identidade admin) ---

resource "aws_iam_user" "backup_uploader" {
  name = "${var.name_prefix}-backup-uploader"
  path = "/qmind/"
  tags = {
    Purpose = "qmind-pgdump-put-only"
  }
}

#tfsec:ignore:aws-iam-no-policy-wildcards
resource "aws_iam_user_policy" "backup_uploader" {
  name = "${var.name_prefix}-backup-uploader"
  user = aws_iam_user.backup_uploader.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "PutDumpOnly"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = ["${aws_s3_bucket.backups.arn}/${var.backup_prefix}*"]
      },
      {
        Sid      = "ListBackupPrefix"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = [aws_s3_bucket.backups.arn]
        Condition = {
          StringLike = {
            "s3:prefix" = ["${var.backup_prefix}*", var.backup_prefix]
          }
        }
      },
      {
        Sid    = "DenyDeleteAndGet"
        Effect = "Deny"
        Action = [
          "s3:DeleteObject",
          "s3:DeleteObjectVersion",
          "s3:GetObject",
          "s3:GetObjectVersion",
        ]
        Resource = ["${aws_s3_bucket.backups.arn}/*"]
      },
      {
        Sid    = "DenyEvidence"
        Effect = "Deny"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.evidence.arn,
          "${aws_s3_bucket.evidence.arn}/*",
        ]
      },
      {
        Sid      = "CloudWatchBackupMetric"
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = ["*"]
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "QMind/Homolog"
          }
        }
      },
    ]
  })
}

# Impede exclusão de backups pelos usuários do servidor (defense in depth)
resource "aws_s3_bucket_policy" "backups_no_server_delete" {
  bucket = aws_s3_bucket.backups.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyDeleteFromServerUsers"
        Effect = "Deny"
        Principal = {
          AWS = [
            aws_iam_user.app_evidence.arn,
            aws_iam_user.backup_uploader.arn,
          ]
        }
        Action = [
          "s3:DeleteObject",
          "s3:DeleteObjectVersion",
          "s3:PutBucketPolicy",
          "s3:DeleteBucketPolicy",
        ]
        Resource = [
          aws_s3_bucket.backups.arn,
          "${aws_s3_bucket.backups.arn}/*",
        ]
      },
    ]
  })
}
