# SEGSENSE_REV_012 — Revisão de aderência do PRM_012

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_REV_012 |
| Versão | 1.1 |
| Status | Corretivo único executado; **não** autoaprovado |
| Data | 12/09/2026 |

## Matriz requisito → evidência → lacuna

| Requisito | Evidência | Lacuna |
|---|---|---|
| `/` é entrada pública SegSense | `App.tsx`; `SegSenseHomePage`; `SEGSENSE_UX_005` | Visual 1440/768/390/320 e zoom 200% **não** verificados em browser desta sessão |
| Icatu não é home | Link para `/demonstracao/icatu`; testes | — |
| Sem exemplo agrícola na vitrine | Página demo com continuidade familiar; testes negativos | Fixtures de `/c/{token}` e catálogo ainda usam “safra” em testes, não na vitrine |
| ASM_001 no índice | Cópia em `documents/`; SHA-256 `4B58089CAB33A774D8ECF137EBE466CB876545294FA591356ADD2B567312DC34` | Escada permanece hipótese |
| SRC_002 | Hub, `/apis` HTML, termos, institucional, Essencial (marketing) | Operações de API **REQUER ACESSO AUTORIZADO** |
| Mock só conceitual | `SEGSENSE_MCK_001`; sem pasta/serviço | PRM_013 bloqueado |
| Sem PWA | `index.html` sem service worker | — |
| CORS não usado para esconder rota | CORS inalterado nesta etapa | — |
| `/c/{token}` visual | — | **Não verificado**; sem login fictício; **não** é argumento de venda |
| SAT-03 | — | **NÃO IMPLEMENTADO** |
| Descoberta a partir de `/admin/demonstracoes` 401 | Links públicos na tela de bloqueio (`SEGSENSE_PRM_012_COR_001`) | Sem IdP; editar/aprovar/publicar permanece indisponível |

## SAT-01 a SAT-10

| SAT | Situação |
|---|---|
| SAT-01 | PARCIAL |
| SAT-02 | PARCIAL |
| SAT-03 | **NÃO IMPLEMENTADO** |
| SAT-04 | PARCIAL |
| SAT-05 | PARCIAL |
| SAT-06 | N/A |
| SAT-07 | N/A |
| SAT-08 | PARCIAL |
| SAT-09 | ATENDIDO |
| SAT-10 | ATENDIDO |

## Corretivo único `SEGSENSE_PRM_012_COR_001`

Não haverá segundo corretivo desta etapa. Ressalvas visuais persistentes seguem para o próximo prompt original.

### Desvio observado (inspeção independente do usuário)

1. Em `http://127.0.0.1:5178/`, texto e rota estavam corretos, mas o hero desktop tinha painel direito quase vazio (três linhas no meio), H1 em quatro linhas e CTAs abaixo da primeira dobra em ~1265×900.
2. A faixa “Em validação — Prova visual da jornada pública e identidade administrativa” expunha pendência de QA interna ao visitante B2B.
3. “A Spider não é dona do SegSense” é verdade arquitetural, porém formulação defensiva para vitrine.
4. A superfície efetivamente usada, `http://127.0.0.1:5178/admin/demonstracoes`, mostrava só o bloqueio de autenticação, sem saída visível para a vitrine pública. Melhorar `/` isoladamente não resolvia “não vejo o que mudou”.

### Mudança aplicada

- Hero da home em composição compacta de uma coluna; painel vazio absorvido; estados **Hoje** / **Depois de contratos**; logo da home reduzido sem alterar o convite `/c/{token}`.
- Linguagem comercial positiva no texto principal; `Satellite Contract` e independência da Spider na seção técnica secundária; sem “Em validação” nem “Spider não é dona” na vitrine.
- Em `/admin/demonstracoes` no estado 401: links “Ver apresentação pública do SegSense” (`/`) e “Ver cenário demonstrativo Icatu — não oficial” (`/demonstracao/icatu`). Sem endpoint admin, login fictício ou afrouxamento de autorização.
- Demo Icatu: badge de fronteira “Ainda depende de contrato”; disclaimer e privacidade preservados.

### Evidência pós-correção

| Prova | Resultado |
|---|---|
| Testes de frontend (conteúdo, navegação raiz, 401 com links, ausência de afirmações enganosas) | Ver devolutiva desta etapa |
| Lint, build frontend e `mvnw.cmd verify` | Ver devolutiva desta etapa |
| HTTP `GET /`, `/demonstracao/icatu`, admin 401 | Ver devolutiva desta etapa |
| Viewports 1440×900, 768×1024, 390×844, 320×568, zoom 200%, teclado | **Não executado** nesta sessão (sem browser real disponível ao agente). Não marcar como prova visual feita. Aceite visual permanece com o usuário. |

PRM_013 **não** iniciado.
