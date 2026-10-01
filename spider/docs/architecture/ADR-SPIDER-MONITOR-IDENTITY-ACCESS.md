# ADR — Acesso por identidade ao Monitor da Spider (sandbox)

Status: aceito no sandbox AWS em 30/09/2026. Não é produção.

## Contexto

O Monitor em `monitor.spider.actionhub.com.br` ficava atrás de um WAF CloudFront com `default BLOCK` e uma allowlist IPv4 `/32` do operador. O endereço residencial mudou várias vezes (`.16` → `.92` → `.77` → nova mudança em 30/09/2026) e o acesso voltava a 403 antes de S3, SPA e backend.

A allowlist de IP dinâmico não é identidade. Atualizar o `/32` só restaura o acesso até a próxima troca de modem/CGNAT.

## Decisão

1. Não reutilizar IdP corporativo: a conta não tem IAM Identity Center, não tem OIDC provider IAM e os User Pools existentes (`panne-prod`, `qmind-homolog-users`) são de outros produtos.
2. Provisionar Amazon Cognito User Pool exclusivo `spider-sandbox-monitor` em `us-east-2`, managed login, Authorization Code + PKCE, sem self-signup.
3. Autenticar o viewer no CloudFront com Lambda@Edge (`viewer-request`, versão imutável em `us-east-1`).
4. Manter WAF ativo como proteção de aplicação (métodos, managed rules, rate limit). O IP residencial deixa de ser requisito do Monitor.
5. Servir a API operacional do console em `/v1/console/*` na mesma origem do Monitor. A API canônica em `api.spider.actionhub.com.br` permanece separada.
6. Não publicar senha, e-mail de operador ou segredo de origem no código. O operador é convidado por CLI.

## Arquitetura

```text
Navegador
    ↓ HTTPS
CloudFront + WAF (default BLOCK + allow de métodos/caminhos)
    ↓ Lambda@Edge OIDC
    ├── S3 privado + OAC — SPA
    └── /v1/console/* — ALB (prefix list CloudFront + header de origem)
            ↓
        ECS sandbox (inalterado nesta entrega)
```

Sessão: cookie `__Host-SpiderId` (ID token, `Secure`, `HttpOnly`, `SameSite=Lax`, 60 minutos). Sem `localStorage`. Sem client secret no bundle. Refresh token não é persistido; expiração exige novo login.

Grupo único autorizado: `spider-sandbox-operators`.

## WAF

- Default `BLOCK`.
- Managed rules: IP reputation, Common Rule Set (cookie size em count), Known Bad Inputs.
- Rate limit 2000 / 5 min / IP.
- Allow GET/HEAD/OPTIONS em qualquer caminho (para o autenticador redirecionar).
- Allow POST/PUT/PATCH/DELETE só em `/v1/console/*`.
- A regra `allow-sandbox-origins` (IP) é fallback temporário e não é identidade.

## Proteção da origem

- S3 continua privado; OAC intacto.
- ALB :443 aceita o prefix list `com.amazonaws.global.cloudfront.origin-facing` e, para a API canônica, a allowlist técnica já existente.
- CloudFront envia `x-spider-origin-secret` só na origem ALB. O WAF regional libera `/v1/console` apenas com esse header.
- Sem esse header, o console não entra pelo ALB mesmo a partir de um IP CloudFront de outra distribuição.

## Separação

| Caminho | Autenticação |
|---|---|
| Monitor humano | Cognito + Lambda@Edge |
| `/v1/console/*` via Monitor | sessão OIDC + header de origem |
| `api.spider.actionhub.com.br` canônico | autenticação técnica já existente; sem login interativo |
| Callbacks / CAP-021 / RDS | fora de escopo |

O backend ECS não foi republicado para preservar a persistência `memory` e a execução `r3`. A identidade assinada é o JWT validado no edge; o edge injeta `X-Spider-Credential-Ref=sandbox-operator` só depois dessa validação. O header solto do navegador não atravessa o autenticador sem sessão.

## Custos adicionais (ordem de grandeza)

Cognito MAU do sandbox (faixa gratuita típica) + Lambda@Edge (centavos em tráfego baixo) + regras WAF extras (~USD 1–5). Total adicional estimado **USD 5–12/mês**, sem NAT e sem RDS.

## Rollback

1. Restaurar a associação anterior da distribuição `E2E4ORTD4DHI1D` (versão CloudFront anterior).
2. Reativar `monitor_ip_fallback_enabled = true` e a allowlist `/32` vigente se precisar de acesso temporário por IP.
3. Não destruir o User Pool. Não tocar ActionHub. Sem `terraform destroy`.

## Validação (30/09/2026)

- Sem sessão: HTTP 302 para o hosted UI, gerado pela Lambda@Edge, não 403 de IP.
- Operador do grupo: login, SPA, `GET /v1/console/executions` = 200, `r3` visível, Simulação e Documentação no nav.
- Identidade autenticada fora do grupo: página `Acesso negado`.
- Logout: volta ao formulário Cognito; nova visita sem sessão.
- Health checks Route 53 (apagados depois) em us-east-1, us-west-1, us-west-2, eu-west-1, sa-east-1, ap-northeast-1, ap-southeast-1 e ap-southeast-2 receberam 302. Nenhuma edição de IP set foi necessária.
- A saída atual do operador já não alcança a API canônica pelo `/32` antigo (timeout no ALB); o Monitor mesmo assim autentica. Isso confirma que o `/32` residencial não é requisito do Monitor.

## Limitações

- MFA é opcional no pool.
- Sessão de 60 minutos sem refresh silencioso.
- Sem IdP corporativo federado.
- API canônica ainda pode usar allowlist IP como controle técnico, independente do Monitor.
- O backend ECS não foi republicado: o JWT é validado no edge; a task `:5` continua com a credencial de sandbox injetada só após essa validação.
