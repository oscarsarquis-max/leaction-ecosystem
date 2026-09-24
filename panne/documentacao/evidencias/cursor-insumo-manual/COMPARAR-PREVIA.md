# Comparação com a prévia aprovada de 960 px

As capturas abaixo são da aplicação React autenticada em `http://127.0.0.1:5180`, com sessão fake e organização descartável. Nenhuma veio de `file://` nem de `/entrar`.

| Tela | URL visível | Largura | Arquivo |
|---|---|---|---|
| consolidar-antes-1440 | http://127.0.0.1:5182/componentes/ingredientes/consolidar | 1440 | capturas/consolidar-antes-1440.png |
| consolidar-selecao-1440 | http://127.0.0.1:5182/componentes/ingredientes/consolidar | 1440 | capturas/consolidar-selecao-1440.png |
| consolidar-depois-1440 | http://127.0.0.1:5182/componentes/ingredientes/consolidar | 1440 | capturas/consolidar-depois-1440.png |
| consolidar-390 | http://127.0.0.1:5182/componentes/ingredientes/consolidar | 390 | capturas/consolidar-390.png |
| abertura-antes-1440 | http://127.0.0.1:5182/componentes/estoque/abertura | 1440 | capturas/abertura-antes-1440.png |
| abertura-erro-1440 | http://127.0.0.1:5182/componentes/estoque/abertura | 1440 | capturas/abertura-erro-1440.png |
| abertura-desconhecido-1440 | http://127.0.0.1:5182/componentes/estoque/abertura | 1440 | capturas/abertura-desconhecido-1440.png |
| abertura-depois-1440 | http://127.0.0.1:5182/componentes/estoque/abertura | 1440 | capturas/abertura-depois-1440.png |
| abertura-390 | http://127.0.0.1:5182/componentes/estoque/abertura | 390 | capturas/abertura-390.png |
| nota-revisao-1440 | http://127.0.0.1:5182/gestao/compras/entradas/e4f213a8-5451-4dfc-9a7a-2968f199c8ff | 1440 | capturas/nota-revisao-1440.png |
| nota-revisao-390 | http://127.0.0.1:5182/gestao/compras/entradas/e4f213a8-5451-4dfc-9a7a-2968f199c8ff | 390 | capturas/nota-revisao-390.png |
| consolidar-previa-960 | http://127.0.0.1:5182/componentes/ingredientes/consolidar | 960 | capturas/consolidar-previa-960.png |

## Alinhamento com a prévia de 960 px

- A rota `/componentes/ingredientes/consolidar` usa `.manual-path` com `max-width: 960px`, papel creme, tinta grafite e acento espresso — o mesmo recorte da prévia HTML aprovada.
- Em 1440 px o conteúdo permanece centrado em 960 px; as laterais são fundo, não outra composição.
- Em 390 px a mesma página empilha destino, compras, conteúdo e o botão final sem corte da ação.
- Abertura e revisão da nota seguem o mesmo papel e a URL real da sessão.

Organização de ensaio: Ensaio insumo (descartável) (c7b1dbca-b26d-419b-bcda-ec352f319128).
