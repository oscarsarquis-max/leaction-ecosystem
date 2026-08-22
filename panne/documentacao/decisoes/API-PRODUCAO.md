# ADR — API HTTP de produção

A API versionada é a única porta de entrada operacional. Routers resolvem contrato, contexto, sessão runtime e mapeamento de erro. Regras de domínio permanecem nos módulos de planejamento e execução.

- Prefixo: `/api/v1/organizations/{organization_id}/production`
- Toda rota exige access token, associação ativa, permissão e RLS
- Organização da rota deve coincidir com a associação selecionada
- Sessão `get_runtime_session` — nunca administrativa
- Comandos: `Idempotency-Key` (UUID), `X-Correlation-Id`, `If-Match` quando há `row_version`
- Decimais como string; timestamps ISO 8601 com timezone
- Schemas `extra="forbid"`
- Sem custos, estoque, PDF/HTML, frontend ou IA operacional
