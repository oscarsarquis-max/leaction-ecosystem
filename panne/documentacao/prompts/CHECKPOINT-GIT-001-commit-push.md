# CHECKPOINT-GIT-001 — Commit e push da Panne

Este é somente um checkpoint operacional de Git após o CURSOR-015.

O usuário iniciou a aplicação localmente apenas para visualizar a interface. Isso não foi deploy.

O CURSOR-016 não foi iniciado e não está autorizado neste pedido.

## Objetivo

Criar commits e fazer push do estado aprovado da Panne até o CURSOR-015, preservando integralmente as demais aplicações e alterações preexistentes do workspace.

## Restrições

- Não iniciar nem implementar o CURSOR-016.
- Não alterar funcionalidades.
- Não acessar MySQL, FTP, AWS, Cognito ou Bedrock reais.
- Não fazer deploy, PR, tag ou release.
- Não executar pull, merge ou rebase automaticamente.
- Não usar push forçado, reset destrutivo ou limpeza de arquivos.
- Não versionar `.env`, credenciais, tokens, chaves privadas ou URLs autenticadas.
- Não incluir alterações, logs, dumps ou artefatos de outras aplicações.

## 1. Inspeção inicial

Antes do staging, verifique e registre:

- branch atual;
- remoto e upstream;
- situação da branch em relação ao upstream;
- commits locais ainda não enviados;
- `git status --short`.

Pode executar `git fetch` para verificar o remoto.

Pare sem criar commit se:

- não houver remoto ou upstream adequado;
- a branch estiver atrás ou divergente;
- existirem commits ou alterações de terceiros que não possam ser isolados;
- o push exigir sobrescrita do histórico;
- existir algum segredo no conteúdo pretendido.

## 2. Documentação

Registre este pedido integralmente em:

`panne/documentacao/prompts/CHECKPOINT-GIT-001-commit-push.md`

Atualize `panne/documentacao/INDICE.md`, indicando:

- CURSOR-015 concluído;
- CHECKPOINT-GIT-001 em execução;
- CURSOR-016 pendente e não iniciado.

## 3. Escopo do primeiro commit

Inclua somente:

1. Todo o conteúdo legítimo de `panne/` produzido e aprovado até o CURSOR-015, incluindo backend, frontend, migrações, testes, documentação e evidências visuais intencionais.
2. Somente os trechos referentes à Panne em:
   - `infra/ecosystem-databases.sql`;
   - `leaction-ecosystem.code-workspace`.
3. O prompt deste checkpoint e a atualização do índice.

Examine os diffs desses dois arquivos do workspace antes do staging. Se contiverem alterações misturadas, selecione somente os trechos da Panne. Se não for possível isolá-los com segurança, pare.

Não inclua:

- `.env` ou configurações locais;
- `.venv`, `node_modules`, caches, cobertura ou builds temporários;
- logs, dumps ou `_lan-sync`;
- arquivos preexistentes de outras aplicações;
- dados reais ou segredos;
- qualquer trabalho do CURSOR-016.

Não introduza Git LFS ou outra infraestrutura nova.

## 4. Segurança do staging

Antes do commit:

- examine `git diff --cached --stat`;
- examine integralmente `git diff --cached`;
- procure no conteúdo staged por senhas, tokens, chaves AWS, chaves privadas e URLs autenticadas;
- confirme que nenhum `.env` está staged;
- confirme que arquivos de exemplo possuem somente placeholders;
- execute `git diff --cached --check`;
- confirme que nenhuma aplicação irmã entrou no staging.

Se encontrar algo indevido, retire somente esse item do staging. Não apague nem modifique o arquivo de trabalho do usuário.

## 5. Validações

Reexecute:

- testes do backend no Python 3.12;
- `pip-audit`;
- typecheck do frontend;
- lint do frontend;
- testes Vitest;
- build de produção do frontend;
- Alembic, cujo head esperado é `0013_legacy_role_label`;
- `/health` e `/ready`, quando o ambiente local estiver disponível.

Os resultados anteriores — 199 testes backend, 1 ignorado e 17 testes frontend — são apenas referência. Registre os resultados reais desta execução.

Se houver regressão, vulnerabilidade ou head inesperado, não faça commit nem push.

## 6. Primeiro commit

Use a convenção existente do repositório. Se não houver uma convenção identificável, use:

`feat(panne): establish production planning platform`

O commit deve conter exclusivamente o escopo aprovado.

Faça push da branch atual para o upstream já configurado.

Não crie outro remoto, não mude a branch de destino e não force o push. Se o push for rejeitado, pare e informe a causa.

## 7. Retorno documental

Depois da confirmação do primeiro push, crie:

`panne/documentacao/retornos/CHECKPOINT-GIT-001-retorno.md`

Registre:

- branch e nome do remoto, sem URL sensível;
- hash completo e mensagem do primeiro commit;
- escopo versionado;
- validações e resultados;
- head do Alembic;
- resultado do push;
- arquivos deliberadamente excluídos;
- estado restante do Git;
- alterações preexistentes que permaneceram fora;
- confirmação de ausência de segredos;
- confirmação de ausência de deploy, PR, tag e release;
- confirmação de que o CURSOR-016 não foi iniciado.

Atualize o índice e faça um segundo commit contendo somente o retorno e essa atualização.

Use a convenção do repositório ou:

`docs(panne): record git checkpoint`

Faça push desse segundo commit para o mesmo upstream, sem força.
