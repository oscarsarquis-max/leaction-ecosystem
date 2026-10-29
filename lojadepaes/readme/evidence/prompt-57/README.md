# Prompt 57 — correção da resposta culinária do Gigio

## Causa comprovada

A pergunta curta **não** excedeu limite de entrada. O laço de ferramentas (`MAX_TOOL_ROUNDS` + 1 chamadas com tools) esgotava sem texto final. O backend devolvia a mensagem fixa «A consulta ficou longa demais. Tente uma pergunta mais direta.» e anexava **todos** os links coletados das ferramentas (vitrine + receita em destaque), sem o modelo tê-los recomendado.

Reprodução em `prod-20261001a` (antes): HTTP 200, ~6,5 s, `unavailable=false`, mesma mensagem, links Pão Fermentação Natural de Trigo, Pão de Café (Marroquinus) e Pan con Tomate. Continuação com histórico repetiu o mesmo erro.

## Correção

- No máximo duas consultas de ferramenta e uma síntese **sem** ferramentas, com pedido explícito de resposta ao cliente.
- Links só se o texto citar o nome ou o href.
- Busca de pães por tokens da pergunta (a frase inteira não precisa estar no nome).
- Timeout/vazio: «Não consegui concluir a resposta agora. Tente novamente.» + `unavailable` e botão «Tentar novamente».
- Limite de entrada continua 422 «a mensagem é longa demais».

## Provas

| Tipo | Onde |
|---|---|
| Isolada (gateway scriptado) | `tests/test_gigio.py` |
| Isolada navegador | `isolated-1440.png`, `isolated-390.png` |
| Bedrock real, catálogo de teste | `tests/test_gigio_live.py::test_live_chat_exact_culinary_question` |
| Produção antes | `repro_before.py` |
| Produção depois | `repro_after.json`, `prod-1440.png`, `prod-390.png` |

## Produção depois (`prod-20261001b`)

Pergunta exata: HTTP 200, ~9 s, `unavailable=false`, três ideias de serviço, um link citado (`Pão Fermentação Natural de Trigo`). Sem «longa demais». Continuação «sem queijo» manteve o pão e não alegou ausência de alergênicos. Fermentação × sova: dimensões distintas que podem coexistir. Receita publicada: só `Pan con Tomate (Tartine Bread)` quando pedida.
