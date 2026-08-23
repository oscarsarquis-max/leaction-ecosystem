# Especificação canônica — Oficina + Atelier

Única direção visual autorizada para orientar o CURSOR-017. Atelier, Oficina e Mesa permanecem no laboratório como histórico.

## Conflitos resolvidos

| Tema | Prevalece | Origem | O que foi descartado |
|---|---|---|---|
| Shell, header, nav, trilho | cromado grafite, caixa alta, trilho sempre visível | Oficina | header claro e nav Georgia do Atelier; pílulas da Mesa |
| Densidade do chrome, badges, pin operacional | compacta e operacional | Oficina | chrome arejado do Atelier |
| Assistente | gaveta temporária à direita | Oficina | folha inferior do Atelier; overlay da Mesa; barra permanente |
| Página central | 8vw, H1 Georgia, grade de cartões, palco + auxiliar | Atelier | seções empilhadas e H1 caixa-alta da Oficina |
| Tabelas de gestão | padding 0,85rem, arejada | Atelier | célula 0,28rem da Oficina |
| Faixa de estado na linha | inset 3px | Oficina | linha sem estado visual |
| Login | cartão editorial, logo completo | Atelier | login estreito e borda pesada da Oficina |
| Header autenticado | logo horizontal; compacto &lt; 980 px | decisão de marca | texto “Panne”; sumiço da marca |
| Impressão | logo completo, P&B, A4 | Atelier + ficha | chrome na folha |
| Mesa | nenhuma peça | — | inspetor permanente, overlay, chips |

## Cores e semântica

| Token | Valor | Uso |
|---|---|---|
| `--bege` | `#E5E4D6` | fundo da aplicação |
| `--bege-alto` | `#F4F3EB` | cartão, painel, login |
| `--bege-baixo` | `#D5D4C5` | trilho de progresso vazio |
| `--grafite` | `#323334` | header, texto, pin |
| `--grafite-suave` | `#4A4B4C` | breadcrumb, meta |
| `--linha` | `#C8C7B8` | bordas de conteúdo |
| `--ok` | `#2F5D3A` | sucesso / completo |
| `--atencao` | `#8A5A12` | pendência |
| `--erro` | `#8B2E2E` | bloqueio / conflito |
| `--info` | `#2F4A5D` | estado em curso |
| `--foco` | `#1D4F73` | `:focus-visible` |

Contraste bege/grafite ≈ 10:1 (AA/AAA). Estado nunca só por cor: badge tem texto e ponto.

## Tipografia

- Chrome e menus: Segoe UI, caixa alta, peso 650 — **Oficina**.
- Título de página (`h1`): Georgia, `clamp(2rem, 4vw, 3.1rem)`, peso 400 — **Atelier**.
- Corpo e tabelas: Segoe UI. Sem webfont externa.

## Grade e largura

- Conteúdo: padding horizontal `8vw` — **Atelier**.
- Palco: `minmax(0,1fr) minmax(14rem, 20rem)` até 980 px; depois uma coluna.
- Cartões e operacional: `repeat(auto-fit, minmax(16rem, 1fr))`.
- Login: máximo 28 rem, centrado.

## Espaçamento

- Conteúdo: `--espaco-conteudo: 1.6rem` — **Atelier**.
- Chrome: gaps 0,2–0,6 rem — **Oficina**.
- Breadcrumb: `0.75rem 8vw 0`.

## Superfícies e bordas

- Header: grafite, raio `--raio-chrome: 0.12rem`.
- Cartão/painel/login: `--raio-conteudo: 1.15rem`, borda `--linha`.
- Gaveta: raio 0, borda esquerda 3 px grafite — **Oficina**.

## Densidade de gestão

Tabela arejada (0,85 rem), caption visível, ação de criação dentro da página. **Atelier**.

## Densidade operacional

Faixa de estado na linha, ação crítica pinada, alvos 40 px. **Oficina**. Grade de blocos no lugar da pilha. **Atelier**.

## Botões

Altura mínima `--alvo: 2.5rem`. Primário no fluxo; pin operacional só na execução. Sem ação só no hover.

## Formulários

Vírgula decimal (`7,250`), `inputmode="decimal"`. Rascunho sintético; sem CRUD real. Campos persistidos visualmente em conflito.

## Tabelas

Caption obrigatória. Gestão arejada; produção com faixa. Ação por papel (Executar some na leitura).

## Filtros

Papel, estado e menu no laboratório. No produto futuro: filtros no palco, não no cromado.

## Menus

Domínios horizontais + trilho sempre visível. Gestão oculta sem permissão. Clique e teclado; Escape fecha.

## Breadcrumbs

`Início / domínio / tela`, no ritmo 8vw do Atelier.

## Badges

Operacionais e de qualidade. Texto + ponto. Semântica em `BADGES-E-GAMIFICACAO.md`.

## Progresso

Barra grafite sobre bege-baixo. Tarefa (pesagem/etapas) e aprendizagem (assistente/ficha) convivem, sem ranking.

## Gamificação

Só coletiva e de qualidade. Proibições em `BADGES-E-GAMIFICACAO.md`.

## Assistentes

Gaveta temporária. Ver `ASSISTENTES.md`. Sem barra lateral permanente.

## Diálogos

O assistente é o diálogo principal (`role="dialog"`). Não há modal de confirmação destrutiva neste laboratório.

## Alertas e erros

Painel no palco: vazio, carregando, conflito, erro, bloqueio. Texto explica; não sugere bypass.

## Responsividade

Desktop 1440, notebook 1366, tablet 1024×768 e 768×1024, monitor 1920, A4. Compacto no header &lt; 980 px. Ver `RESPONSIVIDADE.md`.

## Impressão

A4, 14 mm, logo completo, chrome oculto, P&B.

## Movimento reduzido

`prefers-reduced-motion`: sem animação nem transição. Já em `base.css`.

Nenhuma biblioteca de componentes foi escolhida.
