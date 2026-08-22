# CURSOR-001 — Criar a fundação da aplicação Panne

## Objetivo

Crie a fundação executável da nova aplicação **Panne** dentro do workspace Git `leaction-ecosystem`, respeitando as convenções existentes.

Esta etapa deve entregar backend e frontend mínimos funcionando. Não implemente funcionalidades de negócio.

## Nome e posicionamento

- O nome da aplicação é **Panne**.
- O identificador técnico deve ser `panne`.
- `leaction-ecosystem` é apenas o workspace compartilhado.
- O workspace contém outras aplicações.
- Crie a Panne como uma aplicação independente e irmã das aplicações existentes.
- Não incorpore a Panne dentro de outra aplicação.
- Não altere, reorganize ou prejudique as demais aplicações.
- Não use nomes como “Panne IA”, “Panne App” ou “Leaction Panne”.

## Contexto do produto

Panne é uma plataforma de inteligência de panificação com dois pilares:

1. Criação e adaptação de fichas técnicas por IA, com grounding em receitas e fontes identificáveis.
2. Conformidade com normas regulamentares e técnicas, usando fontes oficiais versionadas, vigência, citações, evidências e revisão humana.

## Restrição absoluta sobre o legado

Existe um sistema anterior desenvolvido em PHP e MySQL. Ele serve somente como fonte de conhecimento do domínio.

Não copie:

- código;
- consultas SQL;
- estrutura física do banco;
- diretórios;
- telas;
- menu;
- identidade visual;
- textos;
- jornadas;
- fluxos;
- arquitetura.

A aplicação Panne será inteiramente nova.

## Stack desta fundação

- PostgreSQL;
- Python 3.12;
- FastAPI;
- SQLAlchemy 2 em modo assíncrono;
- Alembic;
- Pydantic 2;
- pytest;
- React;
- TypeScript;
- Vite;
- Node.js LTS compatível com o workspace;
- gerenciador de pacotes já utilizado pelo workspace.

Use containers somente se forem o padrão do workspace ou necessários para executar o PostgreSQL local de forma reproduzível.

## Arquitetura inicial

Use um monólito modular no backend.

Crie limites inicialmente mínimos para:

- `identity_organization`;
- `reference_library`;
- `ingredient_catalog`;
- `formula_lab`;
- `calculation_engine`;
- `knowledge_grounding`;
- `compliance`;
- `technical_documents`;
- `ai_orchestration`.

Não implemente as regras desses módulos e não os transforme em microsserviços nesta etapa.

## Implementação obrigatória

1. Examine as instruções e convenções existentes no workspace antes de alterar arquivos.
2. Identifique como as aplicações irmãs estão organizadas.
3. Crie um limite próprio e inequívoco para `panne`.
4. Mantenha configurações, dependências e comandos específicos da Panne dentro desse limite.
5. Altere arquivos compartilhados somente quando forem índices ou configurações obrigatórias do workspace.

### Backend

Crie o backend FastAPI com:

- ponto de entrada da aplicação;
- configuração por variáveis de ambiente;
- endpoint `GET /health`;
- resposta estruturada indicando que o serviço está ativo;
- estrutura modular definida anteriormente;
- configuração inicial do SQLAlchemy;
- configuração inicial do Alembic;
- nenhuma tabela de negócio;
- teste automatizado do endpoint de saúde;
- lint e formatação conforme o padrão do workspace.

Se o workspace não possuir padrão para Python, adote uma configuração mínima, atual e documentada.

### Frontend

Crie o frontend React com TypeScript e Vite contendo:

- página inicial inteiramente nova;
- identificação da aplicação como **Panne**;
- mensagem de que o produto está em fase de fundação;
- consulta ao endpoint `/health`;
- estado de carregamento;
- estado de sucesso;
- estado de falha;
- teste automatizado proporcional ao padrão adotado no workspace.

Não crie sistema visual definitivo, dashboard ou menu funcional nesta etapa.

### Execução e documentação

- Configure a execução local reproduzível do frontend, backend e PostgreSQL.
- Forneça `.env.example` sem credenciais.
- Crie ou atualize o README da Panne com pré-requisitos, configuração, execução, testes e estrutura.
- Crie uma área `documentacao/` dentro do limite da Panne.
- Registre este prompt integralmente em `documentacao/prompts/`.
- Crie um arquivo separado para registrar o retorno da execução.

## Não fazer nesta etapa

- Não acessar ou copiar o sistema legado.
- Não implementar autenticação.
- Não implementar usuários ou empresas.
- Não implementar ingredientes.
- Não implementar receitas ou formulações.
- Não implementar fichas técnicas.
- Não implementar conformidade.
- Não integrar Bedrock, Claude ou outra LLM.
- Não criar infraestrutura AWS.
- Não fazer deploy.
- Não adicionar dados reais.
- Não adicionar credenciais.
- Não reutilizar código de outras aplicações apenas porque estão no mesmo workspace.
- Não fazer commit ou push sem autorização explícita.
- Não antecipar etapas futuras.

## Critérios de aceite

- O backend inicia localmente.
- `GET /health` responde com sucesso e contrato estável.
- O teste do backend passa.
- O frontend inicia localmente.
- O frontend exibe o estado obtido da API.
- O teste do frontend passa.
- PostgreSQL e Alembic estão configurados sem tabelas de negócio.
- Lint e formatação do backend passam.
- A verificação TypeScript passa.
- O build do frontend passa.
- Não existem segredos versionados.
- O README permite que outro desenvolvedor execute a fundação.
- A Panne está isolada das outras aplicações.
- As demais aplicações permanecem preservadas.
- Nenhuma funcionalidade de negócio foi antecipada.

## Validações obrigatórias

Execute e registre:

- testes do backend;
- lint e formatação do backend;
- testes do frontend;
- verificação TypeScript;
- build do frontend;
- validação inicial do Alembic;
- inicialização integrada ou verificação equivalente;
- `git diff --check`;
- `git diff --stat`;
- `git status --short`.

## Retorno obrigatório

Ao terminar, entregue:

1. resumo da implementação;
2. localização adotada para a Panne;
3. árvore dos arquivos criados e alterados;
4. decisões tomadas para compatibilidade com o workspace;
5. comandos executados;
6. resultados dos testes, lint, tipos, build e migrações;
7. resumo de `git diff --stat` e `git status --short`;
8. alterações preexistentes que foram preservadas;
9. riscos, limitações, dúvidas e pendências;
10. confirmação de que não houve cópia do legado;
11. confirmação de que nenhuma funcionalidade futura foi antecipada.

Não avance para o próximo prompt.

Não faça commit, push ou deploy.

Aguarde a revisão do arquiteto.
