# ACTIONFINANCE_PLN_001 — Sequência de prompts

## Controle

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_PLN_001 |
| Versão | 0.1 |
| Status | Orientativo |
| Data | 25/09/2026 |

A numeração orienta a ordem. Não autoriza o Cursor a encadear prompts sozinho. Cada prompt detalhado será produzido pelo analista, executado pelo Cursor e devolvido com evidências. Correções usam prompt COR associado.

| Prompt | Entrega | Gate |
|---|---|---|
| PRM_001 — Arquitetura | Documentação, ADRs, evidências e lacunas | Revisão do analista e do responsável; sem runtime |
| PRM_002 — Fundação | Estrutura independente, PostgreSQL, migrations mínimas, health, segurança demo e testes | Depois da revisão da arquitetura; prompt posterior completo |
| PRM_003 — Domínio de contas a pagar | Contrato HTTP próprio, invariantes e persistência de obrigações | Empresa, dinheiro, concorrência, idempotência e histórico |
| PRM_004 — UX operacional | Shell e jornada cadastro/lista/detalhe | Revisão visual, acessibilidade e estados reais |
| PRM_005 — Contratos Spider | Evolução financeira e vínculo de interação/resultado | Gate na Spider e regressões existentes |
| PRM_006 — Primeira integração | Provider mock fiel a contrato aprovado, inbox/outbox e Monitor | Evidência ponta a ponta, sem dinheiro real |
| Posteriores | Recebíveis, caixa, conciliação, Panne, custos e planejamento | Um domínio ou integração por vez |
