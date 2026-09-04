# Gate Cortex — Fluxo produtivo visível + Gigio (adendo pós-028-D)

**Status:** implementação local pronta para revisão. **Não publicar** até autorização do Cortex.  
**Produção / banco `panne`:** congelados. Sem commit/push sem autorização.

> **Adendo obrigatório (Cortex):** validação responsiva integrada — ver `GATE-CORTEX-MOBILE-TABLET.md` e `documentacao/evidencias/cursor-028-mobile/`.

## 1. Wireframe textual da nova entrada

```
[Cabeçalho]
  Logo · Fluxo (pin destacado) · Org · … · menu

Após login/org → /fluxo

┌─────────────────────────────────────────────────────────────┐
│ Fluxo produtivo                                             │
│ Compras→Conferência→Estoque→Produto→Receita→Acabamento→Gestão│
│ Perfil · Organização · Etapa N de M                         │
├─────────────────────────────────────────────────────────────┤
│ [Avatar Gigio]  Você está na etapa K — Título               │
│                 Finalidade · Situação · Pendência           │
│                 [Próxima ação segura]  [Abrir etapa]        │
├─────────────────────────────────────────────────────────────┤
│ Painel: onde / pronto / atenção / N/A / próxima / bloqueio  │
├─────────────────────────────────────────────────────────────┤
│ [1] [2] [3] [4] [5] [6] [7] [8]  ← estados humanos          │
├─────────────────────────────────────────────────────────────┤
│ Detalhe da etapa + ações reais (sem botão morto)            │
│ Etapa 1 lista subpassos fiscais (captura→estoque)           │
└─────────────────────────────────────────────────────────────┘

Nas telas da jornada:
  [Trilha: Fluxo · Etapa N de M · Voltar ao fluxo]
  [Coach Gigio recolhível — orientação sem abrir o chat]
  [conteúdo da tela]
  [avatar flutuante → chat completo]
```

## 2. Mapa de etapas e rotas

| # | Etapa | Rotas principais | Observação |
|---|--------|------------------|------------|
| 1 | Compras e entradas | `/gestao/compras/entradas*` | Inclui 028-D (captura→match→check→confirm→estoque) |
| 2 | Ingredientes e estoque | `/componentes/ingredientes`, estoque, lotes | |
| 3 | Produtos | `/produtos*` | Produto independente (028-C) |
| 4 | Receitas | `/receitas*` | Pode ser **Não se aplica** (comprado/combo) |
| 5 | Planejamento e ordens | `/ordens`, `/planejamento`, `/producao` | |
| 6 | Preparo e execução | `…/executar`, fichas | |
| 7 | Produto acabado e rotulagem | `/conformidade*` | |
| 8 | Custos e preços | `/gestao/custos*` | Oculta sem permissão (`hideWithoutAccess`). Proprietário autorizado **vê** como etapa 8 de 8. |

Home pós-login: `/fluxo`. Pin no cabeçalho + trilha + “Voltar ao fluxo”.

## 3. Regras de estado e próxima ação

Estados humanos: **Não iniciado | Em andamento | Requer atenção | Pronto | Não se aplica | Sem acesso**.

Fonte: `frontend/src/fluxo/resolve.ts` + `orientation.ts`.

- Evidências reais: summary fiscal, products summary, totais de ingredientes/receitas/ordens/estoque.
- Etapa 1: atenção se `awaiting_match|awaiting_check|divergent > 0`; importar/localizar **não** marca concluído (domínio 028-D).
- Etapa 4: comprado dominante sem receita → **Não se aplica**; `produced_without_recipe > 0` → **Requer atenção**.
- Etapa 8 sem permissão → ocultada; orientação diz para seguir acabamento.
- `buildOrientation` só recomenda links permitidos (`allowed: true`); UI não renderiza ação se `!allowed`.

## 4. Gigio por perfil e modalidade

| Modalidade | Comportamento |
|------------|---------------|
| Comprado | Pula ênfase de receita/OP; nota explícita; CTA para acabamento/gestão |
| Produzido | Exige receita vigente antes do planejamento |
| Intermediário | Produto → receita → consumo por outra receita |
| Misto | Nota: escolher origem por abastecimento |
| Combo | Nota: não tratar como receita (slot preparado; inferência ainda limitada aos campos do summary) |

Perfis (`profileFocus.ts`): baker → etapa 6; owner → 1; regulatory → 7; etc. Coach limpa cache ao trocar `organization_id`.

Identidade: `frontend/images/avatar_gigio.png`, alt `Gigio, assistente da Panne`. IDs técnicos `assistant.*` preservados.

## 5. Telas ainda isoladas (fora da trilha)

Exemplos que **não** disparam trilha/coach automaticamente:

- `/inicio` (legado; home real é `/fluxo`)
- `/gestao/relatorios`, inventários, necessidades de compra (fora do matcher de etapa)
- Assistentes de domínio (ingrediente/receita/custo) — mantêm título próprio; o orientador global é Gigio
- Configurações / org / login público (Gigio só como ajuda de entrada)

## 6. Testes e build

Arquivos:

- `frontend/src/fluxo-028b.test.tsx` (legado fluxo)
- `frontend/src/fluxo-gigio.test.tsx` (adendo)
- `frontend/src/assistant.test.tsx`, `guide.test.tsx`, `demo-026.test.tsx` (rótulos Gigio)

Resultado local (2026-08-31):

```
vitest: fluxo-gigio + fluxo-028b + assistant + guide → 28 passed
npm run build → ok (avatar_gigio no bundle; CSS/JS gerados)
```

Comando:

```powershell
cd C:\Projetos\panne\frontend
npm test -- --run src/fluxo-gigio.test.tsx src/fluxo-028b.test.tsx src/assistant.test.tsx
npm run build
```

**Não publicado.** Aguardando autorização do Cortex.
## 7. O que é 028-D vs refatoração do fluxo

| Pertence ao **028-D** (entrada fiscal) | Pertence à **refatoração fluxo + Gigio** |
|----------------------------------------|------------------------------------------|
| Domínio/API fiscal, matching, confirm, stock só após confirmação | `/fluxo` como painel de condução |
| Telas `/gestao/compras/entradas*` | Gigio (avatar, coach, drawer) |
| Migration `0022_fiscal_inbound` | Contrato `orientation.ts` |
| Provider Fazenda (simulado) | Trilha, pin, “Etapa N de M”, estados humanos |
| Docs `entrada-fiscal-mercadorias.md` | Integração visual da entrada como etapas 1.x no fluxo |

**Próxima publicação da demo** deve consolidar: produto independente + entrada fiscal no lugar certo + fluxo visível + Gigio + navegação contextual — **somente após OK do Cortex**.
