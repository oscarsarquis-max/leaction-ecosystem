# ACTIONFINANCE_LAC_001 — Lacunas e pontos a fechar por etapa

## Controle

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_LAC_001 |
| Versão | 0.1 |
| Data | 25/09/2026 |
| Fonte | ACTIONFINANCE_ARQ_001 §14 |

Estas pendências delimitam o próximo detalhamento. Não justificam inventar mecanismos nesta etapa nem bloquear a documentação já possível.

| Antes de | Fechar | Não inventar agora |
|---|---|---|
| Fundação utilizável (PRM_002) | Identidade demo, permissões, versões Maven/npm resolvidas, portas livres, perfil sem fallback | IdP corporativo; READY_FOR_PILOT; Compose sem inventário |
| Domínio (PRM_003) | Campos obrigatórios, teto de valor, unicidade de referência de negócio, correções permitidas, retenção de idempotência | Parcelamento, liquidação, aprovação bancária |
| UX (PRM_004) | Tokens, medidas, obrigatoriedade exata de categoria/centro/unidade | Dashboard, menus vazios, “Todas as empresas” |
| Integração (PRM_005/006) | Contrato financeiro Spider, proveniência por campo, canal de retorno, provider | Webhook fictício; ActionFinance como PROVIDER para contornar o contrato |
| Piloto | Gates corporativos de segurança, operação e dados | Expor diagnóstico interno |

Razão financeiro por partidas dobradas: ADR futuro, não somas de eventos técnicos.

Provider bancário: nenhum aprovado.
