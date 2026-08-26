# Retorno CURSOR-025 — dados demo/smoke e correção do assistente

Ciclo local, sem commit, push ou deploy. Sem CURSOR-026.

## 1. Base, HEAD e cadeia

`main` = `origin/main` = `7086faa` (`fix(infra): include panne in LAN db sync`).

Cadeia local não versionada preservada: `7086faa → CURSOR-022/0019 → CURSOR-023/0020 → CURSOR-024 visual → CURSOR-025`.

## 2. Isolamento e preservação 022–024

Trabalho só em `panne/`. 022–024 não foram revertidos, compactados nem renumerados. Leftovers fora do escopo (`panne/.tmp-chrome-017/`, diffs de `leaction-platform/`, etc.) permaneceram intactos.

## 3. Diagnóstico real do assistente

O 024 afirmou cobertura integral. No produto, o minimizado era botão textual, páginas sem montagem própria ficavam sem avatar, e o overlay de “carregando” podia persistir depois do sucesso. Tratado como falha real: avatar no shell, rotas do router, contexto vivo e limpeza do overlay.

## 4. Avatar minimizado

Botão circular com `compacto-escuro.png`, `aria-label="Abrir assistente da Panne"` (login: “Abrir ajuda para entrar”), tooltip, foco visível, badge acessível, sem animação contínua, `prefers-reduced-motion`, safe-area, oculto na impressão. Logos mestres não alterados.

## 5. Cobertura real das rotas

Assistente no shell autenticado; modo público no login. Lista de rotas = `collectRouterPaths()` sobre `AppRoutes()`. Teste compara router versus guias. Páginas não precisam montar o avatar.

## 6. Contexto vivo

Contrato em `assistant/liveContext.ts`. Guia estático é fallback. Overlay por rota/entidade/estado (ok, loading, vazio, erro, negado). `ListLive` nas listas principais. Loading não fica preso após sucesso.

## 7. Troca de rota, entidade e organização

Mudança de pathname zera overlay/sujo/comando. Troca de organização zera overlay e fluxo. Logout zera tudo. Sem payload integral, token ou segredo no assistente.

## 8. Assistentes específicos

Gaveta única. Mentores específicos reutilizam o mesmo drawer e devolvem o contexto da rota.

## 9. Arquitetura de seed

Reference (catálogos), demo (`panne_demo`), smoke (`panne_smoke` ou transação). Alembic permanece `0020`. Sem `0021`.

## 10. Banco `panne_demo` e guardas

Scripts recusam `panne`, `production`, host não local e sufixo que não seja `_demo`/`_smoke`. Alvo impresso antes do rebuild. Recriado só `panne_demo` (0001→0020). Banco lógico `panne` não foi apagado.

## 11. CLI e scripts

`python -m app.seed` com `reference|demo|smoke|inspect|verify|coverage|dry-run`. Wrappers: `panne/scripts/dev/seed.ps1`, `start-demo.ps1`. Credenciais só do processo.

## 12. Reference seed

Unidades, nutrientes e alergênicos. Idempotente. Migrations 0009 já inserem permissões; reference não duplica papéis.

## 13. Organização e perfis

Panne Demonstração (CENTRAL, BAIRRO) e Padaria Horizonte Demo. Perfis `.invalid` sem senha. Frontend `VITE_DEMO_MODE=1` só fora de produção. Faixa “Ambiente de demonstração”.

## 14. Ingredientes e fornecedores

18+1 (FAR-HZ na org B). Draft/published/retired, nutrição variada, composto MELHOR, preparação CALDA/LEV-POOL. 4 fornecedores, preços históricos e item sem preço vigente.

## 15. Receitas, IA fake e nutrição

PAO-FR, PAO-INT, FOCACCIA, BRIOCHE (publicadas) e BOLO (rascunho sem farinha-base). Trials completed/planned/cancelled. IA só `FakeModelGateway`: proposta revista e proposta vazia. Sem Bedrock.

## 16. Conformidade

Dois dossiês (completo e contexto insuficiente). Sem certificado “Conforme Anvisa”. Fontes sintéticas marcadas Demo.

## 17. Produção

10 ordens: draft, scheduled, released, in_weighing, ready, in_progress, on_hold, completed, short_closed, cancelled. Pesagem, segunda conferência, consumo, rendimento, ficha reemitida, ocorrência bloqueante.

## 18. Custos e preços

Política publicada, cálculo previsto, simulação markup, preço praticado publicado com confirmação reforçada. Sem vendas/faturamento/lucro.

## 19. Relatórios

Visão salva e snapshot no âncora. Cobertura e drill-down pelos serviços existentes.

## 20. Estoque e compras

4 locais, 4 lotes (ok/próximo/bloqueado/quarentena), 2 reservas com adoção histórica. Compras (requisição/pedido) ficaram em lacuna `estoque:compras:recurso_nao_encontrado` — lots e reservas persistiram.

## 21. Editorial local

Provider estático do 024. Sem `actionhub.com.br`.

## 22. Manifesto

`panne/documentacao/evidencias/cursor-025/seed-coverage.md` (+ `.json`). Cenário `025.1`, head `0020_inventory_procurement`, âncora `2026-08-24`.

## 23. Smoke journeys

application, recipe, production, compliance, inventory, reports. application/recipe/production ok no `panne_demo` (2 orgs, 19 ingredientes, 10 ordens).

## 24. RLS e segurança

Duas orgs. FAR-TRIGO ausente na org B. Fake auth só `local|test|demo`. Sem senha, CPF/CNPJ ou e-mail real. Runtime sem fallback admin.

## 25. Alembic head

`0020_inventory_procurement`. Sem migração `0021`.

## 26. Testes backend/seed

Docker Python 3.12: **271 passed, 1 skipped** (`test_ai_bedrock_live`). Inclui 14 testes de seed/guardas. Seed não entra no banco `panne` (transação de teste).

## 27. Testes frontend/assistente

**96 passed**, typecheck, lint (0 erros) e build verdes. Avatar em todos os domínios amostrados; sem botão “Assistente” textual.

## 28. Evidências

`panne/documentacao/evidencias/cursor-025/` — avatar desktop/tablet/mobile, domínios, login/perfis, manifesto.

## 29. Documentação

ADR, segurança, comandos, modelo, manifesto, smoke, perfis, âncora, correção, avatar, contexto vivo, matriz, limitações, prompt e este retorno. `INDICE.md` atualizado.

## 30. Riscos e limitações

Compras demo incompletas. Dry-run sobre base já populada esbarra em imutabilidade pós-liberação. Turno “madrugada” usa código `night`. Auditoria visual live de todas as rotas no app no ar ficou para o `start-demo.ps1`; evidência desta sessão é HTML/PNG + matriz do router + testes de navegação.

## 31. Segredos e Git

Nenhum segredo versionado. Working tree sujo só local. Sem commit.

## 32. Sem acesso externo

Sem MySQL, FTP, `.env`, ActionHub, Bedrock, Cognito, CMS remoto ou apps irmãs.

## 33. Sem commit, push ou deploy

Confirmado.

## 34. CURSOR-026

Não iniciado.
