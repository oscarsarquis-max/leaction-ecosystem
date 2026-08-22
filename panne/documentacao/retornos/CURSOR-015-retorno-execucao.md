# CURSOR-015 — Retorno de execução

## 1. Isolamento

Somente `panne/`. Sem MySQL, FTP, apps irmãs, logos alterados, AWS reais, estoque, custos, offline, IA, commit, push ou deploy.

## 2. Limpeza do rótulo legado

`organization_membership.role` passou a `legacy_role_label` em `0013_legacy_role_label`. Reversível. Contratos ativos usam só `roles`. Autorização ignora o rótulo. Histórico das linhas M2M preservado.

## 3. Logos e cores

`pannebege.png` e `pannepreto.png`: 2000×2000, RGB, sem transparência, margens sólidas. Bege `#E5E4D6`, grafite `#323334`. Logo completo no login/ficha. Cabeçalho usa o nome textual “Panne”.

## 4. Arquitetura e dependências

React + TypeScript + Vite. Nova dependência de runtime: `react-router-dom`. Tipos alinhados ao OpenAPI. Cliente HTTP com cache em memória.

## 5. Autenticação

`AuthProvider` com OIDC+PKCE (sem secret) e fake explícito, bloqueado em produção. Token em memória. Permissões de `/me`.

## 6. Shell

Cabeçalho compacto, navegação horizontal (Produção, Planejamento, Ordens, Rastreabilidade). Em telas estreitas, menu acessível. Sem barra lateral.

## 7. Organização

Associações ativas de `/me`. Seleção obrigatória se houver mais de uma. Preferência local só como conveniência. Troca limpa cache.

## 8. Quadro

Tabela densa de `/production/board`. Filtros na URL. Carregamento, vazio, erro, atualizar e horário. Sem Kanban e sem custos.

## 9. Planejamento e ordens

Listas e detalhes de leitura, paginação, filtros e vínculo plano → ordem.

## 10. Detalhe

Seções de visão geral, materiais, etapas, pesagens, consumos, rendimento, ocorrências, dependências, histórico e emissões. Planejado × realizado.

## 11. Rastreabilidade

Consolidado da API. Sem permissão: acesso negado, não vazio.

## 12. Ficha

Payload canônico + envelope. Impressão A4, sem controles, aviso de substituição/cancelamento. Sem inventar dados. Sem PDF no backend.

## 13. Acessibilidade

Landmarks, labels, foco, contraste AA, estado em texto, axe sem violações críticas.

## 14. Segurança

Sem HTML cru, sem token em `localStorage`, fake bloqueado em produção, cache limpo na troca/logout.

## 15. Estados de erro

401, 403, 404 implícito, 409, 422, 503, vazio, parcial e sessão expirada padronizados.

## 16. Testes backend

**199 passed, 1 skipped.** Python **3.12.14**. `pip-audit` limpo. Migração 0012↔0013 e `0001 → head`. Rótulo legado não autoriza.

## 17. Testes frontend

typecheck, lint, 17 testes Vitest e build de produção. Fake, callback, logout, org, quadro, filtros, planejado×realizado, rastreio negado, ficha, escape, erros e ausência de custos/chamadas proibidas.

## 18. Evidências visuais

`documentacao/evidencias/cursor-015/desktop-amplo.png`, `notebook.png`, `tablet-horizontal.png`, `tablet-vertical.png` e `quadro.html`.

## 19. Documentação

ADR, tokens, logos, arquitetura, OIDC, mapa, quadro, detalhe, ficha, a11y, segurança, erros, evidências, limitações, prompt, este retorno e `INDICE.md`.

## 20. Git e segredos

Nenhum segredo registrado. Nenhum valor de `.env` neste retorno.

## 21. Riscos

Logo horizontal oficial ainda não existe. Estabelecimento e responsável não vêm no payload da ficha. Formulários operacionais ficam no 016. `npm audit` aponta vulnerabilidades transitivas de ESLint; não se forçou `--force`.

## 22. Ausência de commit, push e deploy

Nenhum commit, push ou deploy foi feito. CURSOR-016 não iniciado.
