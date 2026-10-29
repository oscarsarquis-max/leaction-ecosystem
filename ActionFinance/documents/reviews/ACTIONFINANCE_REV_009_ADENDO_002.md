# ACTIONFINANCE_REV_009_ADENDO_002

| Campo | Valor |
|---|---|
| Data | 01/10/2026 |
| Prompt | [ACTIONFINANCE_PRM_009_ADENDO_002_TRANSACOES_REAIS](../prompts/ACTIONFINANCE_PRM_009_ADENDO_002_TRANSACOES_REAIS.md) rev 0.2 |
| Fiscalização | [ACTIONFINANCE_REV_009_ADENDO_002_PARECER_ANALISTA](ACTIONFINANCE_REV_009_ADENDO_002_PARECER_ANALISTA.md) |
| Autorização | Determinação expressa do proprietário neste adendo; não foi pedida outra |
| Aceite | **Não** |

A homologação dos quatro sintéticos **não** é aceite. PRM_007 separado. PRM_010 não emitido. Sem cobrança, payout, baixa ou movimento. Os quatro estados permanecem **não aceites**.

## Inventário da origem (leitura)

Fonte operacional do módulo de pagamentos: `public.orders` no Postgres do Hub, aplicativo em `app_registry`.

| Facto | Valor |
|---|---|
| `app_id` confirmado | `lojadepaes` (não `loja-de-paes`) |
| Empresa AF | `624023a4-57e3-415c-b7d0-925ca1acd3b7` |
| Relação | `public.orders` |
| Janela | 01/10/2026 após correção de classificação |
| Elegíveis REAL (totais operacionais) | **0** |
| Revisão INDETERMINATE | **9** (PAID=7, PENDING=1, CANCELLED=1) |
| sandbox / test_order / live_mode no payload | **ausentes** nestes 9 |
| Prefixo `gateway_ref` | `amount` (checkout avulso) |
| Excluídos | `inove4us` (3), `inove4us-school` (3) — outros apps |
| Testes isolados | `prm009_public_test.orders` = 4, intactos |
| `public.orders` | 15 (inalterado pela leitura) |

Prova no gateway (sem key pública = 401). Loopback POST capability 1.4 após a correção:

- `lojadepaes` + `PRODUCTION` → 200 `itemCount=0` `reviewCount=9` `reviewClass=INDETERMINATE` `reviewStatus=CANCELLED=1,PAID=7,PENDING=1`
- `lojadepaes` + `HOMOLOG` → 403
- `af-public-test-padaria` + `HOMOLOG` → 200 count=4 (schema isolado)
- `inove4us` + `PRODUCTION` → 403

IDs e valores completos ficam nas telas autorizadas; este relato não lista e-mail/nome de cliente.

## 1. Classificação — evidência do checkout

O checkout avulso (`amount-checkout.js`) grava em `external_resource_id`: `source`, `app_id`, `order_reference`, `payment_request_id`, `amount_cents`, `currency`, `description`, `method`, dados de cliente/assunto e retorno. Depois pode acrescentar `mp_payment_id` / `pix`. **Não grava** `sandbox`, `test_order` nem `live_mode`.

A distinção Mercado Pago TEST- versus token live é **do processo** (`isSandboxAccessToken()`). O painel admin “Incluir testes” usa `users.is_test` e e-mails, não uma flag no pedido. Nenhuma destas provas foi persistida nas nove linhas. O prefixo `amount:`, `mp_payment_id` e `payment_request_id` identificam canal/referência; isoladamente não comprovam ambiente real.

Não foi fabricada flag em falta. Não se assumiu teste nem real por ausência. O prefixo do token MP de produção **não** foi consultado (não é evidência por registo e evitaria vazar segredo).

`classifyOrder` só marca REAL com `live_mode=true` (ou `mp_live_mode=true`) no payload. `sandbox=true`, `test_order=true` ou `live_mode=false` → TEST. Caso contrário → INDETERMINATE, com motivo, em `reviews`, fora de `itemCount`. PENDING e CANCELLED da origem foram preservados na revisão.

Paginação: a leitura percorre as linhas SQL até encher a página de elegíveis ou esgotar a origem. O cursor fica na última linha consumida. Prova unitária: TEST + INDETERMINATE no início, CANCELLED REAL a seguir, PAID REAL na página seguinte — os excluídos não encerram a leitura. Hub `spider-pay-lookup.test.js` 16/16 no apply remoto.

## Estados separados (fiscalização)

| Requisito | Estado | Evidência / lacuna |
|---|---|---|
| Importação real no AF | **Pendente de publicação AF/Spider + sessão** | Origem Hub lê os 9 e **não** os afirma REAL. Falta V13+binding `lojadepaes`/`PRODUCTION` no RDS AF, imagem AF com área de revisão, Spider com binding da Loja + `companyId` autorizado + `SPIDER_MONITOR_ALLOWED_COMPANIES` incluindo a Loja, e uma sincronização autenticada. Não foi feito INSERT direto no AF. **Não se afirma que a importação é REAL.** |
| Rastreabilidade pública | **Hipótese pendente; não causa comprovada** | `afm-013a79b8-ffbd-4c82-bcfc-131e10144e1c` é `messageId`. O deep link usa esse id como `execution`. Persistência publicada = memory. Configuração memory demonstra vulnerabilidade a restart, **não** prova sozinha o desaparecimento desta execução. CloudWatch `/spider/sandbox/backend` (retenção 30 dias, ~12 KB) não devolveu o id. Filtro de empresa do Monitor (`SPIDER_MONITOR_ALLOWED_COMPANIES` até agora só Padaria) pode ocultar a Loja **se** o evento ainda existisse. Deploys posteriores são compatíveis com perda, não a demonstram. Correção local: selecionar o id da URL mesmo fora da lista recente. |
| Formato anterior do Monitor | **Código actual ainda tem o formato; prova pública não feita** | `TransactionWorkspace` (“Transação selecionada”), `ExecutionJourney` (DATA PLANE / CONTEXTO / PLANO), etapas expansíveis com detalhe. Não foi substituído por tabela. Comparação visual autenticada **não** feita: login não pedido enquanto as dependências publicadas não estão prontas. |
| Transação canónica 28/09/2026 15:20:33 | **Não recuperada** | Fontes consultadas abaixo. Uma execução nova **não** substitui. Perda declarada até decisão do proprietário. |

## Fontes da canónica e do afm (além do git)

| Fonte | Âmbito / protecção | Resultado |
|---|---|---|
| Artefactos versionados e reviews PRM_009 | Repositório | Id truncado na captura; identificador completo da canónica não localizado. `afm-013a79b8-…` só no prompt/relato. |
| `documents/reviews/evidence/prm-009*` (logs, JSON, capturas) | Evidência local, sem PII extraída | Sem `15:20:33`, `demo-success` nem o afm. |
| CloudWatch `/spider/sandbox/backend` | ECS engine; retenção 30 dias; ~12 KB | 0 eventos para `afm-013a79b8`. `15:20:33` não pesquisável como termo com `:`. Volume residual não contém store de execução. |
| CloudWatch `/actionfinance/web` e `/actionfinance/migrate` | AF; retenção 30 dias | 0 eventos para o afm. |
| S3 do Monitor | Bucket estático do frontend | Não é store de execução. Não consultado como arquivo de jornada. |
| RDS Spider | Módulo Terraform existe; `enable_database=false` | **Não há** base Spider publicada. Nada a consultar. |
| RDS AF / Hub | Produtos distintos; não usados como store da engine | Não se partilhou schema. Não se procurou a canónica lá. |
| Store memory da engine | Volátil; some no replace da task | Estado actual não contém a original. |

Não se promete que alguma destas fontes devesse conter o original. A original **não é recuperável** com o que é acessível. Lacunas: persistência memory, CloudWatch quase vazio, sem exportação/backup do store canónico, id truncado na captura.

## Retenção durável — opções já disponíveis

Não se conclui que seja obrigatório um serviço faturável novo. Nada foi criado.

| Opção | Isolamento | Permissões | Volume / retenção | Custo estimado | Nota |
|---|---|---|---|---|---|
| Manter memory | Processo ECS | Quem lê a API do Monitor | Perde no restart | US$ 0 | Estado actual. |
| Ligar o RDS Spider já modelado (`enable_database`) | VPC privada, SG só da app, DB `spider_orchestrator`, sem partilhar AF/Hub | Runtime Spider + Secrets Manager | `db.t4g.micro`, 20 GB, backup 7 dias | ~US$ 15–20/mês + ~US$ 0,40 Secrets Manager (faixa; não cotada agora) | JPA `JpaOperationalEventStoreAdapter` e Flyway da engine **já existem** no código. Exige aprovação de custo e migration controlada. |
| CloudWatch já existente | Conta AWS / grupo `/spider/sandbox/backend` | IAM de operações | 30 dias; hoje ~12 KB; texto de log | Já pago no sandbox | Não substitui store estruturado de execução. |
| S3 do frontend / tfstate | Buckets de site e estado Terraform | Operações | Irrelevante para jornadas | Já pago | Não usar. |

**Recomendação se houver decisão de custo:** ligar o RDS Spider já previsto, com schema próprio, em vez de criar outro produto ou partilhar a base do Finance/Hub. Sem essa decisão, as restantes tarefas seguem com memory e a perda histórica permanece.

## O que já mudou no código / Hub

- Parecer do analista copiado para `documents/reviews`.
- Hub publicado: REAL só com `live_mode`; nove linhas em `reviews`; paginação por linha lida; PENDING/CANCELLED preservados.
- Contrato 1.4 passa `reviews` / `reviewCount` (Hub, Edge, Spider `ActionHubPayListIdentity`, AF).
- AF: V13 passa a aceitar PRODUCTION e grava `classification` / `classification_reason`. Totais de PRODUCTION só `REAL`. Área de revisão na UI. Sync não para quando a página só tem revisões e ainda há cursor.
- Spider yml: binding Loja → `lojadepaes`; `companyId` da Loja no allowlist do satélite. Task def script inclui as duas empresas no Monitor — **ainda não republicado**.
- UI AF: texto operacional deixa de afirmar importação REAL sem evidência.

## O que falta para a jornada de aceite

1. Migrar V13 e gravar o mapping da Loja (sem apagar sintéticos).
2. Publicar Spider com binding + allowlist da Loja + `SPIDER_MONITOR_ALLOWED_COMPANIES` Padaria **e** Loja (sem abrir todas as empresas).
3. Publicar AF web com a área de revisão e o cliente que persiste reviews.
4. Uma sincronização autenticada na **Loja de Pães** — esperada: 0 no total operacional, 9 em revisão, sem INSERT directo.
5. Comparação visual pública do Monitor com a referência, depois das imagens.
6. Decisão do proprietário sobre a canónica de 28/09 (perda declarada) e sobre ligar o RDS Spider já modelado.

Login não foi pedido: as dependências publicadas ainda não estão prontas.
