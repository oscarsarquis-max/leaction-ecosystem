# Cutover AWS: mudaedu na infra PanelDX (preservada)

> Atualizado: 2026-07-16  
> **inove4us:** intocado.  
> **PanelDX repo / cluster / RDS / ALB:** preservados. Só o domínio `paneldx.com.br` foi desabilitado no ALB.

## Destino

| Recurso | Nome | Ação |
|---------|------|------|
| ECS | `paneldx-cluster` | intacto (serviços ativos) |
| ALB | `paneldx-alb` | + cert SNI mudaedu; regra 503 para host paneldx |
| RDS | `paneldx-database` / `LeAction_SysF` | intacto |
| ECR | `paneldx-backend`, `paneldx-frontend` | intacto |
| R53 mudaedu | `Z0980883GCQKXMRD2S10` | A apex + www → ALB |
| ACM mudaedu | `6aed4833-595b-41b9-b01d-da8023294458` | ISSUED (`mudaedu.com.br` + `www`) |

## Feito

1. ACM `mudaedu.com.br` + `www` (DNS validation na zona mudaedu) — **ISSUED**
2. Alias A `mudaedu.com.br` / `www.mudaedu.com.br` → `paneldx-alb`
3. Cert anexado ao listener HTTPS `:443` (SNI; cert default continua paneldx)
4. Regra ALB **priority 1**: Host `paneldx.com.br` / `www.paneldx.com.br` → **301** para `https://mudaedu.com.br` (path/query preservados)
5. Regra `/api*` movida para priority **10** (continua valendo para `mudaedu.com.br`)
6. SES: `verify-domain-identity` + TXT `_amazonses.mudaedu.com.br` (aguardar Success)
7. **Deploy imagens `v50.0.56`** (build a partir de `mudaedu/`):
   - `paneldx-backend-task:87`
   - `paneldx-frontend-task:92`
   - `leactionf-ai-processor-task:74`
   - Aviso: `PRODUCTION_MASTER_KEY` não estava no ambiente do deploy (gatekeeper unlock/bypass)

## Reverter desabilitação do paneldx.com.br

```powershell
# Remover só a regra 503 (infra permanece)
aws elbv2 delete-rule --region us-east-2 `
  --rule-arn arn:aws:elasticloadbalancing:us-east-2:253137917703:listener-rule/app/paneldx-alb/618ca931d137dc29/b66588a7b2ccb9f1/3748db50b3fddc71
```

## Próximos (app)

- Deploy da imagem a partir de `mudaedu/` (URLs já em `_config.ps1` → `https://mudaedu.com.br`)
- Confirmar SES `Success` + remetentes (`noreply@` / consultor)
- Action Hub webhooks (projeto travado) apontando para mudaedu
