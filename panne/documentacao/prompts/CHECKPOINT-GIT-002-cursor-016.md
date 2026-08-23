# CHECKPOINT-GIT-002 — Registrar e enviar o CURSOR-016

Este é somente um checkpoint operacional de Git. Não autoriza projeto visual, redesign ou CURSOR-017.

## Base esperada

- Branch: `main`
- Upstream: `origin/main`
- Checkpoint anterior: `e6d54f9d15de0019bd846d6faea71f7e6e4ee9af`
- Alembic: `0013_legacy_role_label`
- CURSOR-016 concluído e ainda não versionado
- CURSOR-017 não iniciado

## Objetivo

Versionar e enviar somente a implementação e a documentação do CURSOR-016, preservando as demais aplicações, alterações preexistentes e segredos locais.

## Restrições

- Não iniciar CURSOR-017.
- Não iniciar redesign, nova navegação, CRUDs, badges, gamificação ou assistentes.
- Não alterar funcionalidades.
- Não acessar MySQL, FTP, AWS, Bedrock, Cognito ou aplicações irmãs.
- Não fazer deploy, PR, tag ou release.
- Não usar push forçado, rebase ou reset destrutivo.
- Não limpar arquivos preexistentes.
- Não versionar `.env`, tokens, chaves, credenciais ou URLs autenticadas.

## 1. Inspeção inicial

Antes do staging, registre:

- branch e HEAD;
- remoto e upstream;
- `git status --short`;
- commits locais não enviados;
- situação ahead/behind;
- arquivos alterados desde `e6d54f9d15de0019bd846d6faea71f7e6e4ee9af`.

Pode executar `git fetch`. Não execute `pull`, merge ou rebase automaticamente.

Pare sem commit se:

- a base não descender do checkpoint esperado;
- a branch estiver atrás ou divergente;
- houver trabalho de terceiros sem isolamento seguro;
- existir segredo no conteúdo;
- o push exigir sobrescrita de histórico.

## 2. Documentação

Registre este pedido integralmente neste arquivo.

Atualize `panne/documentacao/INDICE.md`, indicando:

- CURSOR-016 aceito funcionalmente;
- CHECKPOINT-GIT-002 em execução;
- projeto de UX/UI pendente;
- CURSOR-017 não iniciado.

## 3. Escopo do primeiro commit

Inclua somente alterações legítimas em `panne/` produzidas pelo CURSOR-016:

- backend e contratos necessários;
- frontend do modo operacional;
- testes;
- documentação;
- prompt e retorno do CURSOR-016;
- evidências visuais deliberadamente produzidas;
- prompt deste checkpoint;
- índice atualizado.

Não é esperada nova alteração nos índices gerais do workspace. Mudanças fora de `panne/` devem permanecer fora, salvo prova de que pertencem exclusivamente ao CURSOR-016 e eram indispensáveis.

Não inclua:

- `panne/.env`;
- ambientes virtuais;
- `node_modules`;
- caches, cobertura ou builds temporários;
- logs, dumps ou `_lan-sync`;
- artefatos de outras aplicações;
- trabalho posterior ao CURSOR-016;
- protótipos do novo projeto visual.

Confirme que as evidências são intencionais e têm tamanho razoável. Não introduza Git LFS.

## 4. Segurança do staging

Antes do commit:

1. Examine `git diff --cached --stat`.
2. Examine integralmente `git diff --cached`.
3. Procure chaves AWS, tokens, senhas, chaves privadas, credenciais e URLs autenticadas.
4. Confirme que nenhum `.env` real está staged.
5. Confirme que exemplos contêm somente placeholders.
6. Execute `git diff --cached --check`.
7. Confirme que nenhuma aplicação irmã foi incluída.

Se encontrar conteúdo indevido, retire somente esse item do staging. Não apague nem restaure arquivos do usuário.

## 5. Validações

Reexecute:

- backend no Python 3.12;
- `pip-audit`;
- typecheck;
- lint;
- testes frontend;
- build de produção;
- Alembic head;
- `/health` e `/ready`, quando disponíveis.

Referência:

- backend: 201 aprovados e 2 ignorados;
- frontend: 29 aprovados;
- Alembic: `0013_legacy_role_label`;
- `pip-audit`: limpo.

Registre os resultados reais e identifique os dois testes ignorados separadamente. O skip condicionado à URL de runtime não pode esconder fallback administrativo ou regressão de RLS.

Se houver regressão, vulnerabilidade ou head inesperado, não faça commit nem push.

## 6. Primeiro commit

Use a convenção do repositório. Na ausência de alternativa mais consistente:

`feat(panne): add production operator mode`

O commit deve conter somente o CURSOR-016 e a documentação deste checkpoint.

Faça push da branch atual para o upstream existente, sem força. Se houver rejeição, pare e informe a causa.

## 7. Retorno documental

Depois do primeiro push, crie:

`panne/documentacao/retornos/CHECKPOINT-GIT-002-retorno.md`

Registre:

- branch e remoto;
- hash completo e mensagem do primeiro commit;
- escopo incluído;
- validações reais;
- identificação e justificativa dos skips;
- Alembic head;
- resultado do push;
- arquivos excluídos;
- estado restante do Git;
- ausência de segredos;
- ausência de deploy, PR, tag, release e push forçado;
- confirmação de que o projeto visual e o CURSOR-017 não foram iniciados.

Atualize o índice e crie um segundo commit contendo somente o retorno e essa atualização.

Use a convenção existente ou:

`docs(panne): record cursor 016 checkpoint`

Faça push para o mesmo upstream, novamente sem força.

## Retorno ao arquiteto

Informe:

1. branch e remoto;
2. hashes completos e mensagens dos dois commits;
3. resultado dos pushes;
4. escopo incluído;
5. validações reais;
6. skips e suas causas;
7. Alembic head;
8. estado final do Git;
9. arquivos preexistentes mantidos fora;
10. confirmação de ausência de segredos;
11. confirmação de ausência de deploy, PR, tag, release e push forçado;
12. confirmação: **projeto visual não iniciado e CURSOR-017 não iniciado**.

Depois disso, pare.
