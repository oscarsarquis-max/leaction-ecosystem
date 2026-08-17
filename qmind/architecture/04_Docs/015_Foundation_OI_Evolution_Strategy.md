# Estratégia de evolução incremental — Foundation + OI

- Status: **Aprovado**
- Data: 2026-08-17
- ADR: [`../05_ADR/ADR-012-foundation-and-organization-intelligence.md`](../05_ADR/ADR-012-foundation-and-organization-intelligence.md)

## Objetivo

Evoluir o QMind adicionando Organization Intelligence **sem** regressão operacional e **sem** descartar a Foundation.

## Regras de ouro

1. **Aditivo primeiro** — novos módulos/tabelas/APIs; evitar rewrites.
2. **Foundation sem OI** — desligar OI não quebra login, tenant, guided, plan, field, map, PDF.
3. **Uma seta de implementação** — Foundation não importa OI.
4. **Mesmo tenant** — OI usa `OrgContext` + RLS existentes.
5. **Contratos estáveis** — OI consome OpenAPI / facades; não SQL interno de outros módulos.
6. **Bridges explícitas** — dual-read/write documentado; sem migração silenciosa de JSONB guided.
7. **IA subordinada** — ADR-008; humano no loop para decisões técnicas.

## Sequência típica de uma sprint OI

1. ADR curto ou referência a ADR-012 + roadmap fase.
2. Schema org-scoped + RLS (clone do padrão Foundation).
3. API sob org corrente.
4. Hook FE / provider irmão (não inchar `OrganizationProvider` de auth).
5. Testes de isolamento A/B + tenant switch.
6. Integração opcional (Tour/Map/Assistant) atrás de feature clara.
7. Commit coeso; sem misturar refactors Foundation não relacionados.

## Versionamento

| Linha | Como versionar |
|-------|----------------|
| Foundation | v1.0 (ARCH-001); bump v1.x em docs quando houver mudança compatível relevante |
| OI | OI Alpha → OI Beta → OI 1.0 quando houver superfície utilizável em produção |
| Git tags | Preferir tags descritivas (`foundation-v1.0-docs`, depois tags de release de código OI) sem confundir com semver do pacote web |

## Anti-padrões

- Colocar Fit dentro de `maturity_*` sem decisão explícita.
- Passar `organization_id` no body como tenant.
- Fazer Guided Tour depender de serviço OI ainda inexistente.
- “Big bang” de onboarding + Fit + analytics na mesma sprint.

## Próxima sprint recomendada

Ver final do ARCH-001 / relatório de aceite: **OI-0 Foundation Context Bridge** (dual-read Profile ↔ guided / checklist), ainda sem Pain/Fit.
