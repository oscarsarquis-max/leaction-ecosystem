# Publicação sandbox da Spider na AWS

Classificação: **SANDBOX / homologação**. Não é produção.

Padrão Terraform alinhado ao Inove (`hashicorp/aws ~> 5.70`, região corporativa `us-east-2`). Estado remoto próprio da Spider — não reutiliza bucket de outro produto.

## Proteção do ActionHub

Na zona `actionhub.com.br` (`Z01698931CEOITJ7YYMYX`) este código cria **somente** o registro `NS` de `spider.actionhub.com.br`. Não altera `actionhub.com.br`, `www`, `api` nem `school`.

## Ordem

1. `infra/aws/bootstrap` — bucket de state + lock DynamoDB
2. `infra/aws/environments/sandbox` — zona delegada, certificados, rede, ECR, ALB, CloudFront, callbacks preparados
3. Build da imagem e `desired_count` só depois do push no ECR
4. Sync do frontend para o bucket S3 + invalidação CloudFront

## Rollback

Ver `spider/docs/operations/SPIDER-AWS-SANDBOX-001.md`. Não usar `terraform destroy` na zona pai. Remover apenas o `NS` `spider.actionhub.com.br` se for necessário desfazer a delegação.
