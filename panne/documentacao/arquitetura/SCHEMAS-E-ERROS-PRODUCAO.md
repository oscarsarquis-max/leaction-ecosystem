# Schemas e erros da API de produção

- Modelos Pydantic com `extra="forbid"`
- Decimais serializados como string
- Timestamps ISO 8601 com timezone
- Paginação por cursor (`created_at|id`), `limit` ≤ 50
- Texto limitado (64–2000 conforme o campo)

Erros de produção (sem SQL, token ou stack):

```json
{"code": "recurso_nao_encontrado", "message": "Recurso não encontrado."}
```

`/health`, `/ready` e `/me` preservam `{"detail": "..."}`.

| HTTP | Uso |
|---|---|
| 400 | contrato inválido, chave/correlação/ETag ausentes |
| 401 | autenticação |
| 403 | autorização ou organização divergente |
| 404 | recurso inexistente ou invisível (RLS) |
| 409 | estado, idempotência ou concorrência |
| 422 | regra de domínio documentada |
| 503 | dependência indisponível |
