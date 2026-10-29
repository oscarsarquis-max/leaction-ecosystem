# ACTIONFINANCE_REV_007_ADENDO_001 — Gateway existente

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_007_ADENDO_001 |
| Prompt | [PRM_007](../prompts/ACTIONFINANCE_PRM_007.md) + [ADENDO_001_GATEWAY](../prompts/ACTIONFINANCE_PRM_007_ADENDO_001_GATEWAY.md) |
| Data | 30/09/2026 |
| Executor | Cursor |
| Publicação | Continua **não declarada** |
| Aceite | Não atribuído ao executor. Sem PRM_008 |

Complementa [REV_007](ACTIONFINANCE_REV_007.md). Não reabre o PRM_006. Não inicia integração financeira.

## Estado da implantação (antes de qualquer mudança de ingresso)

| Recurso | Estado |
|---|---|
| ALB `actionfinance-alb` | **Existe** desde 30/09 13:40 UTC; 2 AZ públicas da VPC PanelDX; listener 443; idle 60 s |
| Serviço ECS | desired 1, running 1, target **healthy** |
| DNS | `actionfinance.actionhub.com.br` → este ALB |
| Uso ~3 h | 5 pedidos; ConsumedLCUs ≈ 0 |
| Custo de ingresso | parcela DEP_001 §4 **US$ 29,57/mês** (horas + 1 LCU reservado + 2 IPv4) já em curso |
| Ação | **Nenhuma exclusão ou interrupção** |

Login humano e restore isolado continuam pendentes (independentes desta decisão). Dados inalterados: username `admin@actionhub.com.br`, contacto `oscar@oscarsarquis.com.br`, empresa Loja de Pães sem CNPJ.

## Gateway de produção identificado

O analista não o tinha nas fontes da consulta. Leitura na conta `253137917703` / `us-east-2` (sem abrir `C:\Projetos\PanelDX`):

**Ingresso HTTP compartilhado:** ALB `paneldx-alb` (`paneldx-alb-2081687910.us-east-2.elb.amazonaws.com`), VPC `vpc-017dc4cac16ba2c59`. Responsável operacional: o mesmo da conta (IAM `paneldx-user-admin`). Backends: TGs `paneldx-frontend-tg` (:3001), `paneldx-backend-tg` (:5000 `/api*`), `panne-demo-api-tg` (host `api.demo.panne.ia.br`). Certificados SNI: `paneldx.com.br`, `mudaedu.com.br`, `demo.panne.ia.br`. Documentado em `mudaedu/docs/CUTOVER-AWS-MUDAEDU.md` e na auditoria Panne de 28/08.

**Não é esse gateway:**

- EC2 `action_hub_prod` + EIP `3.17.19.188` — processo Hub (`gateway-api`); apex/`www`/`api`/`school` apontam para aqui.
- HTTP API `spider-sandbox-callbacks` — callbacks da Spider; excluído pelo adendo.
- NAT instance e S3 gateway endpoint — saída, não ingresso de browser.

Não há API Gateway REST na região. CloudFront observado é de Panne/Spider, não de `actionhub.com.br`.

## Avaliação das alternativas

| Opção | SPA+API+OIDC+cookie+CSRF | Isolamento de rotas | Custo incremental de ingresso | Afeta outros produtos? |
|---|---|---|---|---|
| Manter ALB AF | Já comprovado no destino | Listener só AF | ~US$ 29,57/mês | Não |
| Host no `paneldx-alb` + TG próprio + regras host prio &lt; 10 | Equivalente (mesmo tipo de hop; app não confia em `X-Forwarded-*`) | Sim, **se** as regras novas forem mais específicas que `/api*` sem host | ~US$ 0–6 (só LCU extra) | Não, se **não** se alterar a regra `/api*` existente |
| API Gateway HTTP API novo + VPC Link | Frágil para SPA/cookies; timeout/payload piores | Só com Cloud Map/NLB/ALB atrás | Extra, e **não** retira ALB se o ALB ficar | Criação nova |
| Proxy no EC2 do Hub | Mistura com gateway-api e pagamentos | Não | Evita ALB AF; SPOF `t3.micro` | **Sim** — Hub |

## Decisão registada pelo executor (técnica; não é aceite do proprietário)

1. O ALB dedicado **não era a única** forma de isolar o ActionFinance. O isolamento exigido (processo, RDS, cookie host-only, Cognito, IAM) já é próprio; o ingresso pode ser host+TG no `paneldx-alb`.
2. **Não migrar automaticamente.** Plano e reversão limitados ao host estão na [DEP_001 §8](../operations/ACTIONFINANCE_DEP_001.md). Sem decisão, o ALB dedicado continua a faturar.
3. **Recomendação:** se o objectivo for deixar de pagar a parcela de ~US$ 30/mês, aceitar a migração da §8.4. Se o objectivo for nunca mutar o listener do `paneldx-alb`, manter o ALB dedicado e assumir esse custo.
4. Recusar Hub EC2 e API Gateway da Spider / API Gateway novo “à frente” do ALB.

Nenhuma alteração foi aplicada ao `paneldx-alb`, ao EIP do Hub, nem ao módulo de pagamentos.
