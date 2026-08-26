# Data-âncora e idempotência

- Âncora explícita: `--anchor-date AAAA-MM-DD`.
- UUIDs determinísticos `uuid5` por chave.
- Segunda execução não duplica organização, estabelecimento nem códigos estáveis.
- Mudança incompatível exige rebuild seguro de `panne_demo` ou `panne_smoke`.
- Dry-run aplica o construtor e faz rollback no CLI.
