# Roadmap arquitetural inicial — QMind OI (Organization Intelligence)

- Status: **Histórico / orientativo** (substituído operacionalmente pela linha ISO Intelligence)
- Data: 2026-08-17 (marcação histórica 2026-08-24)
- Linha: **OI Alpha** (original)
- ADR: [`../05_ADR/ADR-012-foundation-and-organization-intelligence.md`](../05_ADR/ADR-012-foundation-and-organization-intelligence.md)
- Baseline: [`../00_Architecture/004_Foundation_Baseline_v1.md`](../00_Architecture/004_Foundation_Baseline_v1.md)

**Nota (2026-08-24):** a sequência Pain/Fit/Journey abaixo permanece como orientação arquitetural. O eixo de produto ativo é ISO Intelligence (ISOI-001…007+). ISOI-007 é **Core-only** e prepara o contrato futuro de Execution Intelligence (ISOI-009) — ver [`028`](028_ISO_Intelligence_V1_Action_Execution_Workspace.md).

## Princípio

Cada etapa deve ser uma sprint (ou série) **aditiva**, preservando Foundation v1.0. As fases OI-2…OI-5 abaixo **não** são o backlog imediato pós-ISOI-007.

## Fases propostas

### OI-0 — Foundation Context Bridge (próxima recomendada)

- Dual-read Organization Profile ↔ guided session (sem remoção do JSONB).
- Checklist `hasOrgProfile` alinhado ao master data.
- Sem Fit / Pain ainda.

### OI-1 — Organization Context mínimo

- Operational Profile (sites, processos, stakeholders reutilizáveis).
- Extensão controlada do Organization Profile se necessário.
- Consumo inicial pelo Assistente (contexto, sem LLM obrigatório).

### OI-2 — Pain Profile

- Modelo de dores / hipóteses de negócio org-scoped.
- Entrada consultiva; sem scoring automático definitivo.

### OI-3 — Fit Assessment

- Pacote versionado de Fit (paralelo a maturity — não reutilizar SoD de maturity sem ADR).
- Entrada para recomendação de jornada.

### OI-4 — Journey Intelligence

- Recomendação de caminho (Tour / Plan / Field / Map) baseada em Context + Fit.
- Somente sugestão; humano decide.

### OI-5 — Insights e Analytics

- Painéis e agregados org-scoped.
- Eventos/insights que podem sugerir action items na Foundation.

### OI-6 — Governança de IA generativa na OI (se necessário)

- Casos de uso sob ADR-008.
- Sem acesso direto a DB/admin; sem aprovação autônoma.

## Fora de escopo deste roadmap

- Reescrever Evolution Map ou Assistant “do zero”.
- Quebrar RLS / auth.
- Tornar OI pré-requisito para login ou PDF.

## Critério de avanço

Só avançar de fase com: ADR ou emenda se mudar fronteira; testes de isolamento; Foundation utilizável com OI desligada.
