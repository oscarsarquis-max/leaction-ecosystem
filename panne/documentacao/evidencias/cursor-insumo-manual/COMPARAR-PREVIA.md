# Comparação com a prévia aprovada de 960 px

As capturas abaixo são da aplicação React autenticada em `http://127.0.0.1:5183`, com sessão fake e organização descartável. Nenhuma veio de `file://` nem de `/entrar`.

| Tela | URL visível | Largura | Arquivo |
|---|---|---|---|
| estoque-1440 | http://127.0.0.1:5183/componentes/estoque | 1440 | capturas/estoque-1440.png |
| estoque-gigio-recolhido-1440 | http://127.0.0.1:5183/componentes/estoque | 1440 | capturas/estoque-gigio-recolhido-1440.png |
| estoque-gigio-aberto-1440 | http://127.0.0.1:5183/componentes/estoque | 1440 | capturas/estoque-gigio-aberto-1440.png |
| estoque-lotes-expandidos-1440 | http://127.0.0.1:5183/componentes/estoque | 1440 | capturas/estoque-lotes-expandidos-1440.png |
| lotes-1440 | http://127.0.0.1:5183/componentes/lotes | 1440 | capturas/lotes-1440.png |
| consolidar-antes-1440 | http://127.0.0.1:5183/componentes/ingredientes/consolidar | 1440 | capturas/consolidar-antes-1440.png |
| consolidar-selecao-1440 | http://127.0.0.1:5183/componentes/ingredientes/consolidar | 1440 | capturas/consolidar-selecao-1440.png |
| consolidar-depois-1440 | http://127.0.0.1:5183/componentes/ingredientes/consolidar | 1440 | capturas/consolidar-depois-1440.png |
| estoque-390 | http://127.0.0.1:5183/componentes/estoque | 390 | capturas/estoque-390.png |
| estoque-gigio-recolhido-390 | http://127.0.0.1:5183/componentes/estoque | 390 | capturas/estoque-gigio-recolhido-390.png |
| estoque-gigio-aberto-390 | http://127.0.0.1:5183/componentes/estoque | 390 | capturas/estoque-gigio-aberto-390.png |
| estoque-lotes-expandidos-390 | http://127.0.0.1:5183/componentes/estoque | 390 | capturas/estoque-lotes-expandidos-390.png |
| lotes-390 | http://127.0.0.1:5183/componentes/lotes | 390 | capturas/lotes-390.png |
| consolidar-390 | http://127.0.0.1:5183/componentes/ingredientes/consolidar | 390 | capturas/consolidar-390.png |
| abertura-antes-1440 | http://127.0.0.1:5183/componentes/estoque/abertura | 1440 | capturas/abertura-antes-1440.png |
| abertura-erro-1440 | http://127.0.0.1:5183/componentes/estoque/abertura | 1440 | capturas/abertura-erro-1440.png |
| abertura-desconhecido-1440 | http://127.0.0.1:5183/componentes/estoque/abertura | 1440 | capturas/abertura-desconhecido-1440.png |
| abertura-depois-1440 | http://127.0.0.1:5183/componentes/estoque/abertura | 1440 | capturas/abertura-depois-1440.png |
| abertura-390 | http://127.0.0.1:5183/componentes/estoque/abertura | 390 | capturas/abertura-390.png |
| nota-revisao-1440 | http://127.0.0.1:5183/gestao/compras/entradas/1564fc66-3724-4832-9cdc-23b4c971fd79 | 1440 | capturas/nota-revisao-1440.png |
| nota-revisao-390 | http://127.0.0.1:5183/gestao/compras/entradas/1564fc66-3724-4832-9cdc-23b4c971fd79 | 390 | capturas/nota-revisao-390.png |
| consolidar-previa-960 | http://127.0.0.1:5183/componentes/ingredientes/consolidar | 960 | capturas/consolidar-previa-960.png |

## Alinhamento com a prévia de 960 px

- A rota `/componentes/ingredientes/consolidar` usa `.manual-path` com `max-width: 960px`, papel creme, tinta grafite e acento espresso — o mesmo recorte da prévia HTML aprovada (`consolidar-insumo.html`).
- A rota `/componentes/estoque` usa `.estoque-util` com kicker Posição atual, colunas Físico/Reservado/Impedido/Disponível e Ver lotes — alinhada a `estoque-util.html`.
- Em 1440 px o conteúdo permanece centrado; as laterais são fundo, não outra composição.
- Em 390 px Estoque, consolidação e abertura empilham sem cortar a ação final.
- Gigio começa recolhido na visão geral; só abre no acionador explícito.
- Abertura e revisão da nota seguem o mesmo papel e a URL real da sessão.

Organização de ensaio: Ensaio insumo (descartável) (c6f6a5c4-5d19-46c0-926b-52836988c0fa).
