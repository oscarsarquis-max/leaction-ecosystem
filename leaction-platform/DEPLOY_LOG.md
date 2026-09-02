# Deploy log — Action Hub (produção)

Registro operacional de deploys. Uma linha por promoção a produção.

| Data (UTC-3) | Versão | Tag Git | SHA | Ambiente | Resumo | Quem |
|--------------|--------|---------|-----|----------|--------|------|
| 2026-09-02 | 1.0.0 | — | 6dea0b5 | prod | Página pública `/panne` (estática) + assistente comercial local (WhatsApp Hub). Publicação cirúrgica do FE; sem CMS/Demo/Gigio/auth. | Oscar |
| 2026-07-20 | 1.0.0 | actionhub/v1.0.0 | 967a268 | prod | Baseline versionamento go-live | — |
| 2026-07-20 | 1.0.0 | actionhub/v1.0.0 | 095a0b3+ | prod | Cutover MP APP_USR, gate simulação, catálogo R$1/2/3, webhook inove4us | — |

**Publicação 2026-09-02 (`6dea0b5`)**

- URL: `https://actionhub.com.br/panne`
- Processo: upload cirúrgico do frontend Action Hub (`src/app/panne`, marca, isenção de gatekeeper/header) + `npm run build` + `pm2 restart action-hub`. Sem migrate, seed, CMS ou Demo.
- `3252fac` é só documentação deste registro; não entra no rollback funcional.
- Identificação operacional: o health do FE em produção (`GET /api/health`) ainda reporta `git_sha` `3bbe9f0` / `version` `4dcc5cb+3bbe9f0-cms-fe` (env/`GIT_SHA` da caixa). Isso **não** representa o código publicado em `/panne` (`6dea0b5`). A aplicação está no ar; a correção do SHA no health fica para um ciclo futuro.
- Backup `.next` anterior: **não registrado** (sem caminho nem `BUILD_ID` verificados nesta publicação). Restaurar “o `.next` anterior” **não** é rollback válido até existir backup identificado.

Rollback funcional:
- Se houver build anterior identificado por caminho e `BUILD_ID` registrados e verificados: restaurar esse build e `pm2 restart action-hub`.
- Alternativa atual: `git revert 6dea0b5`, reconstruir e publicar **somente** o frontend afetado.
- Não usar `reset`, force push nem atualização integral da EC2. `/inove4us` em produção permanece fora deste commit.

Ao promover: atualize esta tabela **e** confira:
- Gateway: `https://actionhub.com.br` via API interna `/health` (ou proxy) — `version` + `git_sha`
- Frontend: `https://actionhub.com.br/api/health`

### Go-live comunidade (obrigatório)

> **Antes de abrir o público:** eliminar dados transacionais de homologação e **iniciar do zero**.
> Preservar: schema, `app_registry`, `catalog_plans` (SKUs reais ativos), admins seed, configs/secrets.
> Limpar: checkouts/pagamentos de teste, contratos/entitlements de smoke, outbox webhook,
> tracking CRM de teste, posts CMS de rascunho se não forem oficiais — base limpa para a comunidade.

Ordem sugerida: migrate patches → wipe transacional → deploy → smoke pagamento mínimo → unlock gatekeeper (Hub e/ou inove4us).
