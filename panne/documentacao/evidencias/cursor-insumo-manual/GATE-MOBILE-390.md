# Gate mobile 390 — caminho manual de insumo

Prova dirigida do ajuste visual. Aplicação React autenticada (fake local), não HTML estático.

- Frontend: `http://127.0.0.1:5182`
- Viewport 390: `document.documentElement.scrollWidth === clientWidth === 390`
- PNG full-page das rotas 390 com largura intrínseca 390 px
- Desktop 1440: `.manual-path` com 960 px e margem esquerda 240 px (centro do viewport)
- Sem `transform: scale`

| Captura | URL | PNG | scrollWidth |
|---|---|---|---|
| consolidar-390 | http://127.0.0.1:5182/componentes/ingredientes/consolidar | 390px | 390 |
| consolidar-selecao-390 | http://127.0.0.1:5182/componentes/ingredientes/consolidar | 390px | 390 |
| consolidar-sucesso-390 | http://127.0.0.1:5182/componentes/ingredientes/consolidar | 390px | 390 |
| abertura-390 | http://127.0.0.1:5182/componentes/estoque/abertura | 390px | 390 |
| abertura-erro-390 | http://127.0.0.1:5182/componentes/estoque/abertura | 390px | 390 |
| abertura-selecao-390 | http://127.0.0.1:5182/componentes/estoque/abertura | 390px | 390 |
| abertura-sucesso-390 | http://127.0.0.1:5182/componentes/estoque/abertura | 390px | 390 |
| nota-revisao-390 | http://127.0.0.1:5182/gestao/compras/entradas/e4f213a8-5451-4dfc-9a7a-2968f199c8ff | 390px | 390 |
| consolidar-1440 | http://127.0.0.1:5182/componentes/ingredientes/consolidar | 1440px | — |
| abertura-1440 | http://127.0.0.1:5182/componentes/estoque/abertura | 1440px | — |
| nota-revisao-1440 | http://127.0.0.1:5182/gestao/compras/entradas/e4f213a8-5451-4dfc-9a7a-2968f199c8ff | 1440px | — |

Organização de ensaio: Ensaio insumo (descartável) (c7b1dbca-b26d-419b-bcda-ec352f319128).

Não publica. Não altera dados reais. Visão geral do Estoque permanece a atual.
