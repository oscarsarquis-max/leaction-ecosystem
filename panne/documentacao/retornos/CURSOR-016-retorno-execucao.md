# CURSOR-016 — Retorno de execução

Ciclo autorizado em 2026-08-23. Base `e6d54f9d15de0019bd846d6faea71f7e6e4ee9af` (`main` / `origin/main`). Sem commit, push ou deploy. CURSOR-017 não iniciado.

## Incompatibilidades registradas antes da implementação

1. Leituras de materiais, etapas e pesagens não traziam todos os IDs necessários aos formulários.
2. Não havia catálogo autenticado de unidades, tipos e políticas.
3. O payload da ficha não congelava estabelecimento, organização nem responsável.
4. Não havia projeção operacional única para o fluxo do padeiro.
5. O frontend não tinha cliente de comando nem rota `/executar`.

Nenhuma dessas lacunas foi resolvida com backfill fictício, regra de domínio no cliente ou alteração fora de `panne/`.

## 1. Isolamento

Somente `panne/`. Sem MySQL, FTP, apps irmãs, logos alterados, AWS/Bedrock/Cognito reais, estoque, custos, offline, PWA, balança, QR, anexos, WebSocket, SSE ou IA operacional. Artefatos preexistentes de outras aplicações permaneceram fora do escopo e untracked.

## 2. Payload da ficha

`SHEET_TEMPLATE_VERSION` passou a `"2"`. Novas emissões congelam estabelecimento (id, código, nome), organização (id, slug, nome) e responsável (usuário interno, nome de exibição, instante). Não existe responsável de produção no domínio; o campo não foi inventado. Emissões antigas permanecem intactas. Reimpressão lê o JSON persistido. Ausências aparecem como “não informado”. O hash inclui os novos campos. Sem migração física.

## 3. Catálogos

`GET /api/v1/organizations/{id}/production/catalog`, autenticado, permissão `production.order.read`. Expõe unidades de massa `g`/`kg` do cadastro, tipos de rendimento, categorias e severidades de ocorrência, consumos, políticas, estados e decisões já reconhecidos pelo domínio. O frontend só traduz para apresentação.

## 4. Rota e shell operacional

Rota `/producao/ordens/:orderId/executar`, protegida por `production.order.read`. Cabeçalho horizontal compacto (`shell-ops` esconde a navegação secundária). Mostra Panne, organização, ordem, produto, batelada e estado. Retorno ao quadro. Sem barra lateral. Paleta bege `#E5E4D6` e grafite `#323334`. Fluxo: batelada → pesagem → etapas → apontamentos e ocorrências → rendimento → encerramento → ficha.

## 5. Infraestrutura de comandos

`useCommand` + `ApiClient.command`: `Idempotency-Key` por intenção, reuso no retry, chave nova se o conteúdo muda, `If-Match`/`row_version`, `X-Correlation-Id`, bloqueio de duplo clique, sem sucesso otimista, atualização pela resposta do servidor, HTTP 409 com recarregamento, rascunho preservado quando seguro. Erro no painel persistente.

## 6. Pesagem

Sessão por batelada, materiais planejados, registro, valores em string, vírgula pt-BR, unidades só do catálogo, diferença e tolerância do backend, justificativa, reversão/correção por novo lançamento, conclusão/cancelamento da sessão com confirmação, estados pendente/rejeitado/aceito/aguardando.

## 7. Conferência

Política `second_person`: “aguardando conferência por outro usuário”. Aceitar/rejeitar só para usuário distinto do operador. Sem troca de identidade. Orientação para outra sessão autenticada. Validação definitiva no backend.

## 8. Consumo

Consumo, retorno, desperdício e correção. Unidade de massa do catálogo. Motivo obrigatório fora do consumo simples. Resumo planejado/pesado/consumido/retornado/desperdiçado. Sem estoque e sem custos.

## 9. Etapas

Sequência com instrução congelada, tempo, temperatura, estado, operador, início/fim e cronômetro visual reconstruído a partir dos timestamps do servidor. Ações: preparar, iniciar, pausar, retomar, concluir, pular e cancelar, conforme estado e permissão.

## 10. Ocorrências

Categoria, severidade, descrição factual, bloqueio opcional e referência à batelada. Resolução com notas e permissão. Eventos preservados. Sem IA.

## 11. Rendimento

Tipos do catálogo. A tela mostra a projeção do backend: massa final, unidades vendáveis, perda, desvio, completude e tolerância. Sem cálculo de custo.

## 12. Conclusão

Resumo de prontidão da projeção. `completed` pede confirmação explícita. `short_closed` tem apresentação distinta, motivo, permissão específica e confirmação reforçada. Cancelamento vazio não é oferecido depois de iniciada a produção. O backend decide a elegibilidade.

## 13. Ficha e impressão

Listagem, emissão, reemissão referenciando a anterior, visualização e impressão do payload já carregado (`window.print()` sem nova consulta). Snapshots congelados. “não informado” em emissões antigas. Avisos de substituição e ordem cancelada. Sem custos.

## 14. Atualização de dados

Manual, após comando bem-sucedido e polling de 20 s só nesta tela. Para se a aba estiver oculta, se o formulário estiver sujo ou se houver comando pendente. Cancelado ao sair ou trocar de organização. Documentado em `ATUALIZACAO-OPERACIONAL.md`. Sem WebSocket ou SSE.

## 15. Acessibilidade

Labels distintos, teclado, `inputMode=decimal`, alvos de toque, contraste AA, estado em texto, diálogo de confirmação, feedback persistente, `prefers-reduced-motion`, tablet horizontal e vertical. axe sem violações críticas.

## 16. Segurança

Backend autoriza todas as ações. Sem HTML cru. Cache e rascunhos limpos na troca de organização e no logout. Token só em memória. Sem stack, SQL ou token nos erros. `legacy_role_label` não autoriza.

## 17. Testes backend

Python **3.12.14**. **201 passed, 2 skipped.** `pip-audit` limpo. Alembic head `0013_legacy_role_label`. Sem nova migração.

Os 2 ignorados: Bedrock vivo desabilitado (já existente) e `test_runtime_url` porque o runtime local está configurado no container desta estação. Os 3 testes novos (snapshots, catálogo/execução e ausência de `legacy_role_label` na autorização) rodaram.

Regressão da baseline 199: o teste de runtime passou a skip ambiental; não é regressão de domínio.

## 18. Testes frontend

typecheck, lint, **29 testes Vitest** (18 de regressão + 11 operacionais) e build de produção. Cobertura: rota protegida, permissões, idempotência e retry, duplo clique, 409, gramas/quilogramas como string, vírgula, tolerância, reversão/correção, segunda conferência, consumo/etapas, snapshots e impressão sem refetch, emissão antiga sem backfill, limpeza na troca de organização, axe, ausência de custos e de chamada externa real.

## 19. Evidências visuais

Em `documentacao/evidencias/cursor-016/`:

- `executar.html`
- `pesagem.png`
- `etapa.png`
- `ocorrencia-bloqueante.png`
- `resumo-conclusao.png`
- `ficha.png`
- `tablet-horizontal.png`
- `tablet-vertical.png`

## 20. Documentação

ADR, fluxo por ator, comandos, pesagem, consumo, etapas, ocorrências, rendimento, conclusão, ficha/snapshots, atualização, acessibilidade, segurança, evidências, limitações, prompt, este retorno e `INDICE.md`. CURSOR-017 permanece pendente e não iniciado.

## 21. Git, segredos e riscos

HEAD continua `e6d54f9d15de0019bd846d6faea71f7e6e4ee9af`. Working tree só com mudanças da Panne, não versionadas. `panne/.env` permanece gitignorado. Sem segredo gravado. Riscos residuais: o polling não é tempo real; o cronômetro local é só auxílio; a evidência HTML é maquete local, não substitui a página React.

## 22. Ausência de commit, push e deploy

Não houve commit, push, deploy, PR, tag ou release. CURSOR-017 não foi iniciado.
