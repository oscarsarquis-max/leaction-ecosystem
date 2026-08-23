# Ciclo de vida do ingrediente

Não existe `current_version_id`. A versão publicada vigente é a única com `status = published`. Publicar uma nova aposenta a anterior.

```
criar identidade → versão 1 draft → editar rascunho → publicar
                                      ↘ nova versão draft → publicar
publicado → aposentar
identidade active → inactive (arquivamento; sem exclusão física)
```

Regras:

- versão publicada é imutável (trigger + domínio); só transita para `retired` sem alterar o dossiê
- histórico é append-only
- `row_version` + `If-Match` na edição
- comandos com `Idempotency-Key` em `ingredient_command`
- ator e organização ficam no comando e em `created_by_user_id`
