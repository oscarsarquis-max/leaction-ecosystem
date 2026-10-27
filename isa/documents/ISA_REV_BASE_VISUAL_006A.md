# ISA 006A — Base visual

Data da prova: 27/10/2026. Versão `isa-piloto 0.6.17`. Schema permanece 12. Nenhuma regra financeira, rota ou número gravado mudou. O conteúdo de cada tela continua o de 0.6.16; a recomposição para igualar o desenho inteiro fica nos prompts 006B a 006G.

As capturas estão em `documents/reviews/base-visual-006a/`. Os dados da tela são do laboratório, não da conta publicada.

## O que mudou

| Arquivo | Mudança |
|---|---|
| `prototype/styles.css` | Tokens em `:root`. Casca, botões, cartões, faixa, barra, calendário, valores e foco passam a usar só esses tokens. Geist Mono saiu. |
| `prototype/ui.js` | Montagem única de `shell`, `monthControl`, `calendar`, `amount` e `limitBar`. |
| `prototype/app.js` | A casca, a barra e o mês da lista chamam `ui.js`. O título da aba muda no clique, antes da resposta. |
| `prototype/home.js` | Mês e agenda usam a montagem única. O título do mês muda na hora. Entrada e saída levam sinal, seta e cor. |
| `prototype/plan.js` | A grade do planejamento usa o mesmo calendário. |
| `prototype/index.html` | Sai `fonts.bunny.net`. Entram a fonte local e `ui.js`. |
| `prototype/fonts/` | Geist 400, 500, 600 e 700, mais a licença OFL. |
| `server/wsgi_app.py`, `server/serve.py` | Estáticos com `?v=`, cache imutável, gzip em texto. `index.html` e `runtime.js` continuam `no-store`. |
| `prototype/ui.test.mjs` | Montagem de casca, mês, calendário e valor, e contraste dos tokens. |
| `server/test_origem_005t2.py`, `server/test_prod.py` | A cena de 26/10/2026 fica presa nesse dia, porque o relógio do laboratório já é 27/10. O produto continua usando o dia de São Paulo. |
| `VERSION` | 0.6.17. |
| `documents/ISA_CONTINUIDADE_PRODUCAO.md` | Uma frase: 0.6.17 não cria schema e não mexe em dados. |

`limitBar` existe para os prompts seguintes e não foi colocado em nenhuma tela. Não há bloco novo de “Livre para gastar”, gráfico, limites, fila ou alternativas.

## Tokens

| Token | Valor |
|---|---|
| `--marca` / `--marca-hover` / `--marca-suave` | `#1800AD` / `#10007A` / `#EEEBFF` |
| `--ia-fundo` / `--ia-borda` | `#FBFAFF` / `#DCD6FF` |
| `--tinta` / `--texto-2` / `--rotulo` | `#15171C` / `#3A3F4C` / `#5A6072` |
| `--linha` / `--linha-2` / `--controle` | `#E2E4EA` / `#ECEEF2` / `#D5D8E0` |
| `--fundo` / `--cartao` | `#F4F5F8` / `#FFFFFF` |
| `--entrada` / `--entrada-escuro` / `--entrada-fundo` | `#0F766E` / `#0F5F58` / `#E2F3F0` |
| `--saida` / `--saida-escuro` / `--saida-fundo` | `#B4441C` / `#9A3412` / `#FBE6DE` |
| `--atencao-fundo` / `--atencao-borda` / `--atencao-texto` | `#FFF4DF` / `#EBCB8B` / `#7A4E00` |
| título da faixa / `--atencao-barra` | `#5C3A00` / `#9A6200` |

Entrada deixou de ser azul. O azul fica na marca, no link, na aba ativa, no botão primário e no foco. Saída usa `↓ − R$ …` com o menos tipográfico. Entrada usa `↑ R$ …`.

## Contraste

Medido em `prototype/ui.test.mjs`, razão WCAG:

| Par | Razão |
|---|---|
| tinta sobre cartão | 17,93:1 |
| tinta sobre fundo | 16,45:1 |
| texto de apoio sobre cartão | 10,52:1 |
| rótulo sobre cartão | 6,27:1 |
| rótulo sobre fundo | 5,75:1 |
| branco sobre marca | 12,79:1 |
| marca sobre cartão | 12,79:1 |
| entrada sobre cartão | 5,47:1 |
| saída sobre cartão | 5,55:1 |
| atenção sobre a faixa | 6,60:1 |
| título da faixa | 9,35:1 |

Todos ficam em ou acima de 4,5:1. Na faixa roxa, o anel de foco é branco, porque o roxo da marca sobre o roxo da faixa não se vê.

## Capturas

Laboratório isolado, pessoa sintética, em 1440 e 390 px. Rotas: Entrar, Início, Lançamentos, Planejar, Contas, Perfil, Registrar, Importar, Conferir, Pendências, Origem, Detalhe e Lote. Arquivos `{rota}-1440.png` e `{rota}-390.png`.

Não houve rolagem horizontal em 390, 360 nem 768 px.

O mês seguinte troca o título em 0,6 ms, antes da resposta. A aba Lançamentos fica ativa em 0,6 ms, antes da resposta. A palavra “Importar” não aparece no Início.

Zoom de 200% pelo `Emulation.setPageScaleFactor` do navegador, na vista de 390 px do Início: a largura rolável continuou igual à largura da tela. Não foi uma inspeção visual de cada rota a 200% no computador.

## Recortes e diferença de pixel

Comparação da implementação com o HTML de referência, no mesmo navegador. Lado a lado: `*-lado.png`.

| Recorte | Pixels diferentes | Motivo que permanece |
|---|---|---|
| Faixa 1440, 19,4% | 17.904 de 92.160 | O lugar é o da faixa de 64 px. O desenho traz a palavra “ACTION FINANCE” como marcador. A tela usa o ativo oficial `logoisantrans.png`. O nome da conta no laboratório não é o texto fictício do desenho. |
| Navegação 1440, 11,2% | 8.551 de 76.320 | A ordem, a aba ativa e o “+ Registrar” coincidem. A sobra é raster da fonte Geist e do botão. |
| Mês 1440, 11,2% | 6.477 de 57.728 | Os botões e o título ocupam a mesma faixa de 44 px. A linha “Hoje…” usa o dia e a hora reais da resposta, não “segunda 26 · 08:12”. |
| Calendário 1440, 9,8% | 8.881 de 90.820 | A grade e os nomes Dom–Sáb coincidem. No laboratório o dia de referência é 16/10/2026, então “hoje” é 16, e não há as marcas fictícias do desenho. |
| Faixa 390, 11,1% | 2.430 de 21.840 | Mesma troca do ativo oficial da marca. O círculo de iniciais tem 44 px para o toque; o desenho desenha 40. |
| Barra 390, 9,3% | 2.756 de 29.640 | Itens, ícones e o “+” roxo de 48 px coincidem. O selo “7” em Lançamentos é do 006C e não entrou. |

## O que funciona e o que ainda não é o desenho

Funciona: casca de computador e de celular, seletor só em Início, Lançamentos, Planejar e Contas, cabeçalho branco nas tarefas no celular, mês, calendário com forma e legenda, tokens, fonte local, foco e o cache dos estáticos.

Ainda não é o desenho, de propósito:

- O miolo de cada tela (saldo, lista, formulários) continua o de 0.6.16, só com as cores e os componentes novos. 006B a 006G recompõem esse miolo.
- As pílulas de Lançamentos e as abas Lançamentos/Lotes medem 40 px, como o chip aprovado. O critério geral de toque pede 44 px. Ficaram em 40 para não desviar do chip desenhado.
- O selo numérico de Lançamentos não existe ainda.
- “Mês atual” só aparece fora do mês corrente.

## Carga no laboratório

Primeira abertura de `/`: 17 pedidos, 273.076 bytes pelo `Content-Length` (CSS e JS já comprimidos; `styles.css` saiu de 43.791 bytes em disco para 8.858 no fio). Segunda carga, por recarregar a página: os mesmos 17 pedidos e os mesmos bytes. O recarregar pede de novo à rede. Os estáticos responderam `Cache-Control: public, max-age=31536000, immutable`. `/` e `runtime.js` responderam `no-store`. Não houve medição separada da versão 0.6.16 neste laboratório; a diferença conhecida é que aquela versão buscava a fonte em `fonts.bunny.net` e marcava todo estático como `no-store`.

## Testes

`python -m unittest discover -s server -p "test_*.py"`: 113 testes, ok, SQLite e PostgreSQL isolado em `127.0.0.1:5442`.

`node prototype/calc.test.mjs`, `lotes.test.mjs`, `bb-statement.test.mjs`, `recorte.test.mjs`, `regras-mes.test.mjs` e `ui.test.mjs`: ok.

## Publicação

O bloco abaixo é preenchido depois da imagem.
