resource "aws_ecr_repository" "inove4us" {
  name                 = var.project
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "inove4us" {
  repository = aws_ecr_repository.inove4us.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Manter últimas 15 imagens"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 15
      }
      action = { type = "expire" }
    }]
  })
}
