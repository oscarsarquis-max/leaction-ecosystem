# Contratos HTTP — receitas

Prefixo: `/api/v1/organizations/{organization_id}`.

Listagens devolvem cartão (`id`, código, nome, situação, versão corrente). O dossiê completo só entra em `GET /recipes/{id}/versions/{versionId}`.

Comandos de escrita exigem sessão runtime, `X-Correlation-Id` e, quando mutam rascunho, `If-Match`. Criação, versão, publicação, aposentadoria, escala, nutrição, trial e aprovação usam `Idempotency-Key`.

Erros públicos: `{code, message}` em português. Sem SQL, stack ou token.
