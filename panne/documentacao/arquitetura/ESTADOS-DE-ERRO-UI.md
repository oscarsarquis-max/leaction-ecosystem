# Estados de erro da interface

| Estado | Tratamento |
|---|---|
| carregamento | `role="status"` |
| vazio | mensagem operacional, não erro |
| erro recuperável | alerta + tentar de novo |
| sessão expirada | 401 → `/entrar` |
| acesso negado | 403 com texto, não tela vazia |
| API indisponível | 503 |
| conflito | 409 |
| organização sem produção | vazio no quadro |
| dados parciais | aviso no detalhe da ordem |
