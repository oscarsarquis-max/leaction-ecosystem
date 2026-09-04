# Gate Cortex — Experiência mobile e tablet (adendo pós Fluxo + Gigio)

**Status:** correção pontual pós-auditoria aplicada. **Não publicar.**  
Ver também `documentacao/produto/GATE-CORTEX-MOBILE-TABLET.md`.

## Correção pontual (esta rodada)

| Arquivo `fix-*` | Conteúdo |
|------------------|----------|
| `fix-fluxo-8etapas__*` | Proprietário com 8 etapas (390 / 768 / 1440) |
| `fix-trilha-8etapas__celular-390__viewport.png` | Trilha 1…8 em tela participante |
| `fix-fluxo-gigio-compacto__tablet-v-768__viewport.png` | Gigio empilhado no tablet vertical |
| `fix-fluxo-sem-custos__celular-390__viewport.png` | Sem custos → 7 etapas |

Script pontual: `frontend/scripts/capture-028-mobile-gate-fix.mjs` (não regenera as 42).

---

**Produção / banco `panne`:** congelados. Sem CMS. Sem commit/push nesta passagem.

Condicionante do Cortex (aceitação do gate local Fluxo + Gigio): evidências reais de celular/tablet + auditoria de não-sobreposição do Gigio + entradas fiscais 028-D.

## 1. Escopo desta passagem

| Feito | Não feito |
|-------|-----------|
| Apresentação/operação mobile-tablet do Fluxo e do Gigio | Refatorar lógica de orientação / resolve / modality |
| Coach inicia recolhido em ≤720px | Publicar pacote demo consolidado |
| Padding/safe-area para FAB não cobrir CTA/campos | Ligar CMS Action Hub (`config_key=panne`) |
| FAB some com teclado virtual (`visualViewport`) | Commit / push / produção / DB `panne` |
| Auditoria visual das telas fiscais 028-D | |

## 2. Matriz de viewports (canônica)

| Nome | Dimensão | Evidências |
|------|----------|------------|
| desktop-1440 | 1440×900 | fluxo, entradas, entradas-nova, produtos-coach |
| notebook-1366 | 1366×768 | idem |
| tablet-h-1024 | 1024×768 | idem |
| tablet-v-768 | 768×1024 | idem |
| celular-390 | 390×844 | idem + avatar close-up + viewport “não cobre” |

Pasta: `documentacao/evidencias/cursor-028-mobile/`  
Script: `frontend/scripts/capture-028-mobile.mjs` (preview `:5187`, API mockada, sem Hub).

Cada rota gera `*.png` (fullPage) e `*__viewport.png` (primeiro viewport — FAB fixo legível).

## 3. Checklist Gigio (não cobrir)

| Elemento | Comportamento mobile | Evidência |
|----------|----------------------|-----------|
| Painel editorial no `/fluxo` | Empilhado, alinhado à esquerda, CTAs tocáveis | `fluxo__celular-390*.png`, `fluxo__tablet-v-768*.png` |
| Coach recolhível | Sticky; inicia **recolhido** em ≤720px; toggle ≥40px | `entradas__celular-390*.png`, `produtos-coach__celular-390*.png` |
| Avatar flutuante | Canto inferior direito; padding direito/inferior no `.main`; some com teclado | `avatar-flutuante__celular-390.png`, `gigio-nao-cobre__celular-390__viewport.png` |
| Campos / navegação / ações | Reserva de coluna direita; CTAs acima do FAB | viewport shots + teste de overlap |

## 4. Auditoria entradas fiscais (CURSOR-028-D)

Rotas capturadas:

- `/gestao/compras/entradas` — lista + filtros empilhados + coach
- `/gestao/compras/entradas/nova` — quatro vias (manual, XML, PDF/foto, Fazenda preparada)

Sem UUID cru nas evidências de conteúdo; grid de opções em coluna única no celular.

## 5. Alterações de código (apresentação)

- `frontend/src/styles/app.css` — safe-area, padding FAB, coach sticky, fiscal grid
- `frontend/src/fluxo/FlowCoachPanel.tsx` — recolhido em ≤720px; `matchMedia` defensivo
- `frontend/src/assistant/AssistantAvatar.tsx` — oculta FAB com teclado virtual
- `frontend/src/fluxo/useFlowEvidence.ts` — tolera mock sem `items` (sem crash)
- `frontend/src/test-setup.ts` — polyfill `matchMedia` (jsdom)
- `frontend/src/responsive-mobile-tablet.test.tsx` — viewport + overlap CTA
- Ajustes de asserção em testes que passaram a ver coach + detalhe duplicados

## 6. Testes e build

```
vitest run → 35 files / 223 tests passed
npm run build (VITE_AUTH_PROVIDER=fake, VITE_DEMO_MODE=1, VITE_HOMOLOG_DEMO=1) → ok
```

**Não publicar.** Aguardando gate final do Cortex.
