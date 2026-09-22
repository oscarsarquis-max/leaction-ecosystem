# R028-003 — Mapa visual do caminho crítico

## 1. Causa

`/fluxo` tinha oito etapas, estados e Gigio, mas ainda se lia como lista/trilha de módulos. Não distinguia etapa em foco, posição real do caminho, visão geral da organização e jornada de um produto.

## 2. Modelo visual final

Hierarquia:

1. Cabeçalho (título, subtítulo, org/perfil, modos Visão geral / Jornada de produto)
2. **Mapa dominante** (conectores + estados humanos + ícones)
3. Resumo do caminho (posição, pronto, bloqueio, próxima ação, N/A, limitações)
4. Gigio (explica o mapa; não compete)
5. Detalhe da etapa em foco (cartão reduzido)

## 3. Foco × posição

| Conceito | Significado | UI |
|----------|-------------|-----|
| Etapa em foco | Selecionada para consulta (`?etapa=`) | borda tracejada + “Em foco para consulta” |
| Posição real | Primeira etapa aplicável que ainda impede o avanço | “Você está aqui” |
| Ambos iguais | Foco == bloqueio | “Posição e foco” |

Clicar numa etapa **só** muda o foco; nunca inventa “Você está aqui”.

## 4. Visão geral × produto

- **Visão geral:** preparação da organização; mensagem explícita para escolher um produto.
- **Jornada de produto:** estados só com dados do código público (`?modo=produto&produto=CODE`); sem UUID.

## 5. Regras por modalidade

| Modalidade | Etapas N/A ou especiais | Posição típica |
|------------|-------------------------|----------------|
| Produzido | — | Sem receita → Receitas; sem plano → Planejamento; ordem liberada → Execução |
| Comprado | 4–6 Não se aplica — produto comprado | Entrada → produto → acabado → custos |
| Intermediário | 7 pode N/A (não vai à vitrine) | Receita / produção / consumo |
| Combo | 4–6 N/A (não é receita/ordem) | Componentes → comercialização → custos |
| Misto sem origem | 4–6 Requer decisão (origem) | Bloqueio até informar `origem=` |

## 6. Gigio

Textos determinísticos: “Seu caminho está parado em…”, motivo, consequência, próxima ação, preparação vs produto, “Não se aplica”. Sem IA generativa obrigatória.

## 7. Arquivos

- `frontend/src/fluxo/criticalPath.ts` — motor foco × posição × modalidades
- `frontend/src/fluxo/FlowMap.tsx` — mapa
- `frontend/src/fluxo/FlowPage.tsx` — página
- `frontend/src/fluxo/orientation.ts` — Gigio do mapa
- `frontend/src/styles/app.css` — layout responsivo
- `frontend/src/fluxo-critical-r028.test.tsx` + ajustes gigio/028b/fiscal/demo-guide
- Guia R028-002 alinhado: FE `demo/guideFallback.ts`, `DemoGuidePage.tsx`; BE `demo_guide/content.py` (`r028-003`)

## 8. Testes / build

- FE: **244 passed** (+ `fluxo-critical-r028` 10)
- BE: `tests/test_demo_guide.py` — **3 passed**
- Build homolog: `VITE_HOMOLOG_DEMO=1 VITE_DEMO_MODE=1 VITE_AUTH_PROVIDER=fake npm run build` — ok

## 9. Evidências

Pasta `screenshots/`:

| # | Arquivo | Conteúdo |
|---|---------|----------|
| 1 | `01-visao-geral-desktop.png` | Preparação da organização + mapa |
| 2 | `02-produzido-bloqueado-receita.png` | BOLO parado em Receitas |
| 3 | `03-produzido-pronto-execucao.png` | BRIOCHE parado em Preparo e execução |
| 4 | `04-comprado-nao-aplicavel.png` | T028C-BUY com 4–6 N/A |
| 5 | `05-foco-diferente-posicao.png` | Etapa 8 em foco; posição em Compras |
| 6 | `06-mobile.png` | 390-ish (iPhone 12) |
| 7 | `07-tablet.png` | 768×1024 |
| 8 | `08-perfil-sem-custos.png` | Leitor / sem etapa 8 |

Também: `resolution-rules.md`, `routes.md`, `counts-before.json`, `counts-after.json`.

## 10–13. Publicação (demo only)

| Item | Valor |
|------|--------|
| Git SHA | `636b1704fad65383bbad9483ffd24b44a00434bc` (+ commits de evidência/hotfix FE) |
| API digest | `sha256:0599d600f54459e0b09c0e72012c656270f69b92c6957dd596918efbf614f5b4` |
| Task def | `panne-demo-api:11` |
| ECR scan | COMPLETE, CRITICAL=0 HIGH=0 (counts vazios) |
| FE | S3/CloudFront `demo.panne.ia.br` |
| Contagens | delta **0** vs before |
| Produção / Hub / CMS / DB `panne` | não alterados |

### Validação externa

- `GET https://api.demo.panne.ia.br/health` → `demo` / `panne_demo`
- `GET …/api/v1/public/demo-guide` → `content_version=r028-003`, `source=live`
- `https://demo.panne.ia.br/fluxo` e `/demonstracao` → 200
- Hub `https://api.actionhub.com.br/api/health` → 200
