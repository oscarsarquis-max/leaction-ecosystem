# ACTIONFINANCE_REV_005 — Identidade visual e consistência da interface

Versão 0.1 — 29/09/2026. Entrega do PRM_005 no recorte local demonstrativo. Sem autoaprovação. Sem PRM_006. Sem produção/piloto.

## Delimitação

Apresentação apenas. Regras, contratos, permissões, idempotência, recuperação de falhas e saldo/baixa/estorno de PRM_003/004 permanecem. Sem tabela, coluna, migration, seed, cálculo no frontend ou nova função financeira. Sem Spider, Hub, Panne, commit, push ou deploy.

O parecer `ACTIONFINANCE_REV_004_PARECER_ANALISTA.md` **não estava no repositório**. Foi copiado, com o encerramento do analista, da pasta de entregáveis `outputs` em 29/09/2026. Conteúdo e autoria preservados. Este relatório não substitui o parecer.

## Marca

Bytes intactos de `outputs/logos-compactas` para `frontend/src/assets/brand/`. Originais nas duas pastas preservados. Sem geração, recorte ou recompressão.

| Destino | Intrínseco | SHA256 conferido após a cópia |
|---|---|---|
| `frontend/src/assets/brand/actionfinance-yellow.png` | 2098 × 749 | `332179CEB05EFB12B6DB5523D631D787319428FF511D5C97776C4A9F5E8BA1EB` |
| `frontend/src/assets/brand/actionfinance-blue.png` | 2127 × 739 | `AE022ADB1D554D8188849EBA1D8674D57B3804E0F2C8A349823AD490D02AC0EC` |
| `frontend/src/assets/brand/actionfinance-white.png` | 1254 × 1254 | `A29779E088E171BCA42D80BE75199E55A1A2688DC53DE177320C1396EB2AF477` |

Amarela no shell (212 px na sidebar, 144 px no cabeçalho compacto) e na entrada. Azul e branca só no componente `BrandLogo` e no guia UX, para uso futuro. Alt “Action Finance Capital”. `height: auto`; sem `object-fit: cover`.

## Tokens finais

Centralizados em `frontend/src/app.css` (`:root`).

`#14143D` `#24219B` `#1C197E` `#FFE366` `#F4D34F` `#F3F5FB` `#FFFFFF` `#18243A` `#526078` `#818A9C` `#EAEAFE` `#166534` `#854D0E` `#B42318`.

`--border` saiu de `#D7DEEA` (1,35:1 no branco) para `#818A9C` (3,47:1 no branco; 3,18:1 no canvas). Combinações de texto e botão verificadas em `documents/reviews/evidence/prm-005/contrast.txt`. Não é certificação geral de acessibilidade.

Ouro com texto navy. Vencido = ⚠ + warning. Quitado comprovado = success. Sem rodapé “Fundação técnica…” nas páginas operacionais.

## Shell e telas

`AppShell` + `PageHeader` + componentes em `frontend/src/ui/`. Desktop: sidebar 248 px, área clara, ação primária ouro. ≤1023: drawer, Menu, foco/Escape, cartões no lugar da tabela. Formulários até 880 px; selects não parecem botão ouro. Extrato: período visível; três saldos nomeados; rename/inativar secundários.

## Jornadas e provas

| Tipo | O quê |
|---|---|
| Real (UI + API) | Playwright `npm run capture:prm-005`: criar conta, título 150, baixa 50, completar, estornar 50, extrato, obrigação + pagamento 50, viewer sem escrita. Viewports 1280, 768 e 360. Dados próprios (não seed). |
| Inspecionado | Entrada sem token visível; zoom CSS 200% da lista em 1280; `scrollWidth = clientWidth` em todas as capturas. |
| Mock (Vitest) | 24 testes: token, PATCH/register, retry/conflict de título/conta/baixa/estorno, extrato atrasado. Sem reescrita do mecanismo de envio. |
| Teclado | Armadilha de foco do drawer e do `Modal` (já coberta no código); Playwright abre Menu em 360/768 e o diálogo de estorno. Não houve passada humana separada de Tab em todos os campos. |

Dados criados nesta execução (segunda captura, após espera do resumo):

| Viewport | Conta | Recebível | Obrigação |
|---|---|---|---|
| 1280 | Conta jornada PRM 005 desktop-1280-1790692260397 | Recebível jornada PRM 005 desktop-1280-1790692260397 | Obrigação jornada PRM 005 desktop-1280-1790692260397 |
| 768 | Conta jornada PRM 005 tablet-768-1790692264636 | Recebível jornada PRM 005 tablet-768-1790692264636 | Obrigação jornada PRM 005 tablet-768-1790692264636 |
| 360 | Conta jornada PRM 005 mobile-360-1790692268894 | Recebível jornada PRM 005 mobile-360-1790692268894 | Obrigação jornada PRM 005 mobile-360-1790692268894 |

Capturas em `documents/reviews/screenshots/prm-005/`: lista, detalhe, formulário, conta/extrato, modal de estorno, entrada (1280/360), erro de token com alerta e campo vazio, menu mobile aberto, viewer, zoom 200%. Log: `journey-log.json` (também em `evidence/prm-005`).

## Gates

| Gate | Resultado |
|---|---|
| ESLint | 0 erros |
| Vitest | 24/24 |
| `tsc` + Vite build | ok; PNGs da marca no bundle |
| `npm audit` e `--omit=dev` | 0 vulnerabilidades |
| Backend / Flyway | não alterados; verify/backup não repetidos |

## Limitações

- Aceite de identidade/UX é do analista; o Cursor não aprova.
- Contraste relatado só nas combinações listadas.
- Teclado ponta a ponta em todos os campos não foi filmado; drawer/modal e testes existentes cobrem o mecanismo.
- Conflito/retry de rede continua nos Vitest/ITs já aprovados; o Playwright desta fatia não reencenou 409.
- Variantes azul/branca da marca não aparecem nas telas operacionais (proposital).

Prompt integral: `documents/prompts/ACTIONFINANCE_PRM_005.md`. UX atualizado. DAT só com nota de ausência de mudança de modelo. PRM_006 não iniciado.

## Adendo COR_001 — 29/09/2026

Paleta e assets permanecem **aprovados**. Este adendo trata só do cabeçalho compacto e do foco do drawer. Não é autoaprovação final.

### C1

Em &lt;768 px (e também 768–1023, para a coluna do Menu não esticar com o nome da empresa): linha 1 = Menu à esquerda e logo amarela 144 px à direita; linha 2 = empresa; linha 3 = badge + usuário/Sair, com quebra interna. Sem recorte da marca, sem `overflow: hidden` na página, sem posicionamento absoluto sobre a logo. Desktop ≥1024: empresa à esquerda, badge e usuário à direita.

### C2

Contenção de foco, backdrop e `inert` só com `compact && navOpen`. Sair do breakpoint compacto fecha o drawer sem focar o Menu oculto. Destino efetivado fecha e foca `#page-title`. Escape/backdrop devolve ao Menu visível. Formulário sujo recusado mantém a página e o drawer.

### Provas

| Tipo | Resultado |
|---|---|
| Vitest | 28/28. Novos: nomes longos fora da marca; Tab/Shift+Tab/Escape; destino foca o título; resize sem Menu oculto focado; recusa de dirty sem mudar de página |
| Playwright | `capture:prm-005-cor-001`. Caixas menu/logo/usuário sem sobreposição em 360 (fechado, nomes longos, modal). Logo 144 px. Teclado observado no runtime. 768 e 1280 sem regressão de sobreposição |
| lint / build | 0 erros ESLint; `tsc` + Vite ok |
| Backend | não repetido |

Capturas em `documents/reviews/screenshots/prm-005-cor-001/`. Log em `evidence/prm-005-cor-001/header-log.json`. Inspeção visual: em `mobile-360-modal.png` o nome do usuário **não** atravessa a logo. Prompt: `documents/prompts/ACTIONFINANCE_PRM_005_COR_001.md`.

Este ajuste encerra o defeito do cabeçalho descrito no parecer. Aceite focado do analista pendente. PRM_006 não iniciado.
