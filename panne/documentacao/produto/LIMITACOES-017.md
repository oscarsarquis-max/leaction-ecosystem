# Limitações — CURSOR-017

Fora deste ciclo, de propósito:

- Receitas, formulação UI, rotulagem final
- custos, markup, margem, valor de venda, estoque, compras
- upload, importação em massa, crawler, integração externa
- CRUD livre de catálogos globais
- gamificação persistente, ranking, pontos
- IA / Bedrock / Cognito groups
- Python 3.12 não está instalado nesta máquina; a suíte rodou no 3.11.15 do venv oficial da app
- evidências autenticadas dependem do provedor falso local; não há deploy

Incompatibilidades resolvidas neste ciclo: HTTP de ingredientes inexistente; trigger que impedia aposentar publicado; ciclo de composição global; ausência de `row_version` e de `ingredient_command`.
