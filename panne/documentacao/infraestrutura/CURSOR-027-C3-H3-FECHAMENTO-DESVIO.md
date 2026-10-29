# CURSOR-027-C3-H3 — fechamento com desvio (produção congelada)

| Campo | Valor |
|---|---|
| Status | **H3 fechado com desvio documentado** |
| Decisão | Proprietário/Cortex: **produção congelada** durante homologação |
| Prod migrate token | `cursor-027-c3-h3-migrate-prod-authorized-once` — **não executado** (não falhou) |

## Resultados

| Item | Estado |
|---|---|
| Rotação `panne/demo/db/migrator` | OK (task `06ef654c…`, exit 0; senha antiga rejeitada) |
| Stream H2 comprometido | **removido** (`c3h2-demo/…/0501b07f…`) |
| img6 | `backend-027-c3-h3-142b356-img6` @ `sha256:986847550959133ae2a912feac9143dd2922986e16e01d88532a56ca755e7eac` |
| Scan | COMPLETE CRITICAL=0 HIGH=0 |
| Demo migration | **OK** task `4211bc0d…` exit 0; head `0020_inventory_procurement` |
| Fingerprint demo | `d16e92540d7208b6e11fdae5d7c3f5662cdf0e44cd12c199b30ef460d98e97cd` |
| Fingerprint local homologado | **idêntico** (`d16e9254…`) |
| Comparação demo↔prod | **adiada** (produção deve permanecer vazia / não migrada) |
| DB `panne` (prod lógico) | **não migrado, intocado** nesta passagem |
| Produção migration | **deliberadamente adiada** |

## Isolamento / fechamento

- 0 RUNNING/PENDING `panne-db-migration`
- 0 TD ACTIVE
- Task role: somente leitura migrator secrets; **sem** PutSecretValue; **sem** master
- RDS SG: somente `panne-prod-fargate-sg` + `panne-demo-fargate-sg`
- Logs novos: sem URL/credencial; hits de filtro `password` no rotate = flags de status (`postgres_password_altered=true`, etc.)

## Desvio vs plano H3 original

O plano previa migrate prod após demo verde. Cortex/owner **congelou produção** na homologação: não pedir gate separado de migrate prod; não seed/serviço de produção.

## Próximo objetivo (homologação demo)

1. Seed Demo 026 **somente** em `panne_demo`
2. Validação dos dados
3. API demo Fargate
4. Frontend demo S3/CloudFront
5. Certificado + DNS
6. Entrega `demo.panne.ia.br`
