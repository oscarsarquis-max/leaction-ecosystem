# Idempotência e concorrência

- Comandos exigem `Idempotency-Key` UUID
- A mesma chave com o mesmo comando devolve o resultado original
- Chave reutilizada com outro comando → 409 `idempotencia_conflito`
- Recursos versionados exigem `If-Match` com `row_version`
- Versão divergente → 409 `versao_conflito`
- Adoção de política, criação de plano e remoção de item seguem o mesmo ledger de `production_event`
