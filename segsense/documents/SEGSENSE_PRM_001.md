# SEGSENSE_PRM_001 — Criação do ambiente inicial de desenvolvimento

## Controle

- Projeto: SegSense
- Tipo: prompt para Cursor
- Documento-base: SEGSENSE_ARQ_001
- Versão: 1.0
- Data: 04/09/2026

## Prompt para execução no Cursor

Atue como engenheiro de software responsável por criar a fundação técnica do projeto **SegSense** dentro do workspace Git já existente **`leaction-ecosystem`**, atualmente aberto no Cursor. Use a raiz real desse workspace como referência; não presuma que `C:\Projetos\segsense` seja a raiz do código.

Antes de alterar arquivos:

1. inspecione todo o repositório;
2. localize e leia integralmente o documento `SEGSENSE_ARQ_001` na documentação oficial do SegSense;
3. procure e cumpra instruções locais, como `AGENTS.md`;
4. identifique a estrutura, as convenções e os comandos já adotados pelo workspace;
5. preserve documentos, arquivos e alterações preexistentes;
6. verifique o estado do Git sem desfazer alterações;
7. caso exista conflito entre este prompt e a arquitetura documentada, interrompa e relate-o.

O repositório Git já está criado e configurado. Não execute `git init`, não crie repositório aninhado, não altere remotes, branches, hooks ou configurações Git e não mova a raiz do workspace.

### Objetivo

Criar um ambiente local, reproduzível e verificável, contendo backend Java, frontend React, PostgreSQL, espaços reservados para as integrações Spider e Icatu e documentação completa de execução.

Esta etapa cria somente a fundação técnica. Não implemente regras de seguros, jornadas contextuais ou integrações reais ou simuladas.

### Tecnologias

- Java 21 LTS;
- Spring Boot 4.1.x, na correção estável mais recente da linha;
- Maven e Maven Wrapper versionado;
- React 19.2.x;
- TypeScript em modo estrito;
- Vite estável compatível;
- Node.js 24 LTS;
- npm com lockfile versionado;
- PostgreSQL 18, na correção estável mais recente;
- Flyway;
- Docker Compose;
- JUnit 5 e Testcontainers;
- Vitest e React Testing Library.

Não adote Kubernetes, mensageria, service mesh, microsserviços independentes ou infraestrutura de nuvem nesta etapa.

### Estrutura obrigatória

O workspace deverá receber a estrutura do SegSense abaixo. Se o `leaction-ecosystem` já possuir uma convenção explícita para projetos ou módulos, encaixe o SegSense nessa convenção sem criar outro repositório e informe o caminho adotado.

```text
segsense/
├── frontend/
├── backend/
├── services/
│   ├── spider-integration/
│   └── icatu-integration/
├── database/
│   ├── migrations/
│   └── seeds/
├── documents/
├── .editorconfig
├── .gitignore
├── .env.example
├── compose.yaml
└── README.md
```

Não renomeie nem mova a pasta oficial de documentos do SegSense e não altere identificadores dos documentos existentes.

### Backend

Crie uma aplicação Spring Boot modular em `backend`, com package raiz `br.com.segsense` e artifact `segsense-backend`.

Inclua apenas dependências para API REST, validação, JPA, PostgreSQL, Flyway, health/readiness, testes unitários e testes de integração com Testcontainers.

Preserve separação entre domínio, aplicação, entrada HTTP e infraestrutura. Não crie entidades fictícias apenas para preencher a estrutura.

Implemente somente:

- inicialização e configuração externa por variáveis de ambiente;
- conexão real com PostgreSQL;
- execução automática das migrations;
- `GET /api/v1/system/info`, retornando nome, versão e estado operacional sem dados sensíveis;
- health e readiness;
- estrutura padronizada de erros para endpoints futuros;
- teste unitário mínimo;
- teste de integração que inicie PostgreSQL com Testcontainers, aplique migrations e valide a aplicação.

Use UTC e UTF-8. Não registre senhas, tokens, strings completas de conexão ou payloads sensíveis.

### Banco de dados

O PostgreSQL local deverá ser iniciado pelo `compose.yaml` com banco `segsense`, usuário local `segsense`, credenciais por variáveis, volume nomeado, porta configurável e healthcheck.

Mantenha as migrations canônicas em `database/migrations` e configure o backend para localizá-las conforme o modo de execução documentado.

Crie uma migration inicial apenas para validar o versionamento, podendo criar o schema `segsense` e estrutura estritamente técnica. Não crie tabelas funcionais de publicadores, oportunidades, jornadas, usuários ou integrações.

Em `database/seeds`, documente a política futura de seeds. Não inclua dados pessoais ou exemplos confundíveis com dados reais.

### Frontend

Crie em `frontend` uma aplicação React, TypeScript e Vite com:

- TypeScript estrito;
- ESLint e formatação consistente;
- configuração por variáveis do Vite;
- página simples “SegSense — Ambiente de desenvolvimento”;
- consulta real a `GET /api/v1/system/info`;
- estados visíveis de carregamento, backend disponível e backend indisponível;
- testes do componente principal e da indisponibilidade da API;
- layout acessível, responsivo e sem imagens externas.

Não implemente telas de seguros. Não use mock para fazer o backend parecer disponível.

### Integrações futuras

Crie `services/spider-integration/README.md` e `services/icatu-integration/README.md` explicando:

- finalidade futura;
- contratos ainda não fornecidos;
- proibição de inventar endpoints, payloads, credenciais ou comportamentos;
- desacoplamento entre SegSense e sistemas concretos;
- que capability não é sistema, rota ou adapter.

Não implemente clients HTTP falsos ou adapters especulativos.

### Configuração

Crie `.env.example` apenas com nomes e valores locais não sensíveis. Ignore `.env` no Git.

Preveja variáveis para porta, banco, usuário e senha do PostgreSQL, URL JDBC, porta do backend, origem permitida do frontend e URL pública da API. Não versione segredos.

Configure CORS somente para a origem local declarada, sem curinga.

### README

O `README.md` raiz deverá explicar:

1. visão do SegSense;
2. relação entre SegSense, Spider e Icatu;
3. pré-requisitos e versões;
4. estrutura das pastas;
5. preparação do `.env`;
6. inicialização do PostgreSQL;
7. execução do backend em Windows/PowerShell;
8. execução do frontend em Windows/PowerShell;
9. execução de todos os testes;
10. health e readiness;
11. encerramento sem apagar dados;
12. remoção opcional do volume, com alerta de exclusão;
13. solução de problemas comuns;
14. declaração de que Spider e Icatu ainda não estão integrados.

Todos os comandos documentados devem ter sido efetivamente validados.

### Qualidade e segurança

- Fixe dependências por lockfiles e mecanismos dos gerenciadores.
- Não suprima TLS nem validações.
- Não use credenciais reais ou dados pessoais.
- Não crie abstrações sem uso, código morto ou TODOs genéricos.
- Use inglês no código e português claro na documentação.
- Preserve compatibilidade entre Windows e containers Linux.

### Validações obrigatórias

Execute e registre:

1. build e testes do backend;
2. teste de integração com PostgreSQL por Testcontainers;
3. instalação reproduzível do frontend pelo lockfile;
4. lint, testes e build do frontend;
5. validação sintática do Compose;
6. inicialização e healthcheck do PostgreSQL;
7. inicialização do backend conectado ao banco;
8. chamadas reais a system info, health e readiness;
9. inicialização do frontend e leitura real do backend.

Se uma dependência local estiver ausente, não finja validação. Execute o restante e relate o bloqueio, comando afetado e correção necessária.

### Critérios de aceite

- Todas as pastas obrigatórias existem e estão documentadas.
- PostgreSQL inicia pelo Compose e as migrations são aplicadas.
- Backend inicia e responde aos endpoints técnicos.
- Frontend inicia e mostra o estado real do backend.
- Builds, lint e testes passam.
- O repositório não contém segredos.
- Outro desenvolvedor consegue reproduzir o ambiente pelo README.
- Nenhuma regra de seguros foi inventada.
- Nenhuma integração fictícia com Spider ou Icatu foi criada.
- Documentos existentes permaneceram intactos.

### Relatório final

Responda com resumo, árvore relevante, decisões tomadas, arquivos principais, comandos e resultados, evidências da comunicação entre as três camadas, pendências reais e confirmação de que não foi criada integração simulada com Spider ou Icatu.

Não faça commit, push, deploy ou publicação externa sem solicitação expressa.
