# ADR-010 — Homologação econômica (Lightsail)

- Status: Aceito
- Aceito em: 2026-08-04
- Emenda a: `ADR-009-hospedagem-e-operacao.md`
- Emenda Lightsail: 2026-08-04
- Domínio: `qmind.com.br` (Route 53 na conta AWS)
- Responsáveis: equipe QMind

## Contexto

O scaffold Terraform de homologação previa ECS Fargate + ALB + RDS + NAT + autoscaling. Essa forma é adequada como **perfil futuro** (padrão inove), mas o custo e a complexidade são desproporcionais ao momento atual do QMind (homologação e piloto inicial sobre `mvp-fullstack-v0`).

É necessário um caminho de implantação **reproduzível, barato e suficiente**, aceitando ponto único de falha com backups testáveis. EC2 tradicional com Elastic IP foi considerado; **Amazon Lightsail** oferece preço mensal mais previsível (plano + transferência + IP estático associado).

## Decisão

Para **homologação e piloto inicial**, adotar o perfil **`terraform-lightsail`**:

```
Route 53 (qmind.com.br)
   │  api.homolog / app.homolog → mesmo IP
   ▼
Lightsail Ubuntu (plano ~2 GB, IP estático)
   ├── Caddy — HTTPS Let's Encrypt (sem ACM/ALB)
   ├── React — estáticos
   ├── FastAPI
   ├── Worker
   └── PostgreSQL (Docker; porta sem exposição pública)
          │
          ├── disco do plano Lightsail
          └── pg_dump diário criptografado → S3 backups

S3 — evidências | Cognito — OIDC/JWT
```

### Incluído nesta fase

| Componente | Papel |
|---|---|
| Lightsail Ubuntu 24.04 | host único (Docker Compose) |
| Bundle `small_3_0` (~2 GB / ~US$ 12 com IPv4 em `us-east-2`) | compute previsível |
| IP estático Lightsail | DNS; sem cobrança extra enquanto associado |
| Caddy | HTTPS + proxy — sem API Gateway / ACM ALB |
| Cognito | auth JWT/OIDC |
| S3 evidências + S3 backups | objetos e `pg_dump` |
| Firewall Lightsail | só 80/443; SSH temporário se necessário |
| Snapshot Lightsail + restore testado | continuidade |
| AWS Budget US$ 30 | alertas 50/80/100% real e 80/100% previsto |

### Explicitamente fora desta fase

- ALB
- ECS / Fargate
- RDS gerenciado
- NAT Gateway
- Autoscaling
- API Gateway

API Gateway não é necessário com um único servidor público: adiciona custo/complexidade e exige proteger a origem. Caddy/Nginx cobre HTTPS e roteamento sem serviço adicional.

### Perfis Terraform

| Perfil | Caminho | Uso |
|---|---|---|
| **lightsail** (ativo) | `infra/terraform-lightsail/` | Homologação / piloto |
| **enterprise** (futuro) | `infra/terraform-enterprise/` | ECS/ALB/RDS — **não aplicar agora** |
| minimal-ec2 (legado) | `infra/terraform/profiles/minimal-ec2/` | Supersedido — não aplicar |

### Continuidade aceitável com SPOF

1. snapshot da instância Lightsail antes de updates relevantes;
2. `pg_dump` diário criptografado para S3;
3. Terraform + Compose versionados;
4. restore **testado** e documentado.

### Custo-alvo

- Lightsail `small_3_0`: **~US$ 12/mês** (+ S3/Cognito/logs leves → ordem **~US$ 15–25/mês** típico).
- Teto de alerta: Budget **US$ 30**/mês (`qmind-homolog-monthly-30`).
- Ver `infra/COST_ESTIMATE_HOMOLOG.md`.

## Tokens de IA (alinhamento com ADR-008)

Para **tokens de modelo** (não confundir com JWT/OIDC):

- conhecimento persistente em PostgreSQL, S3 e arquivos versionados;
- prompts curtos e específicos; recuperar só trechos necessários;
- não reenviar conversas inteiras; persistir resumos estruturados;
- cache de resultados seguros;
- modelos menores para classificação/extração; modelo caro só quando necessário;
- limites de tokens por caso de uso;
- métricas de custo por organização e operação.

**Tokens de autenticação** (JWT/OIDC Cognito) permanecem obrigatórios e não são substituídos por arquivos ou registros inseguros.

## Alternativas consideradas

### Aplicar imediatamente ECS/ALB/RDS

Rejeitada para esta fase: custo (~55–130 USD/mês com NAT) e superfície operacional altos demais para homologação/piloto.

### EC2 tradicional + Elastic IP (primeira emenda do dia)

Substituída por **Lightsail**: preço mensal previsível (compute + transferência + IP estático associado) sem montar VPC/SG/EIP manualmente.

### API Gateway na frente do host público

Rejeitada: Caddy cobre HTTPS/roteamento; API Gateway adiciona complexidade sem benefício com um servidor.

## Consequências

### Positivas

- Custo alinhado ao momento do produto.
- Operação simples (um host Compose) com Cognito + S3 reais.
- Perfil ECS preservado para quando HA/escala forem necessários.

### Negativas e riscos

- SPOF: indisponibilidade do host derruba o ambiente.
- Postgres em EC2 exige disciplina de backup/restore (não há Multi-AZ RDS).
- HTTPS via Caddy (Let's Encrypt) ou certificado no Nginx — ACM no ALB não se aplica neste perfil.

## Critérios de aceite desta emenda

- [x] ADR-010 aceito; ADR-009 aponta emenda de fase.
- [x] Perfil Lightsail + enterprise (ECS) preservado.
- [x] Budget US$ 30 com alertas por e-mail.
- [x] Estimativa Lightsail (~15–25 USD/mês típico; teto alerta 30).
- [x] `terraform plan` Lightsail gerado (22 add) — revisão humana antes do apply.
- [x] Gate `011` alinhado a Lightsail + `qmind.com.br`.
- [x] Docs 012/013 e ADR-011 integrados ao índice.

## Referências

- `ADR-009-hospedagem-e-operacao.md`
- `ADR-006-autenticacao-e-autorizacao.md`
- `ADR-008-camada-e-governanca-de-ia.md`
- `../04_Docs/011_Homologation_Readiness_Gate.md`
- `../../infra/DEPLOY.md`
- `../../infra/COST_ESTIMATE_HOMOLOG.md`
