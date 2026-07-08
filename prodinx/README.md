# Prodinx

Projeto web para gestão e processamento de dados de produção industrial.

## Visão Geral da Arquitetura

O Prodinx segue uma arquitetura em camadas, com responsabilidades claramente separadas entre interface, API de consumo, serviços de receção de dados e persistência.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│   frontend  │────▶│   backend   │────▶│  banco_de   │◀────│    servicos      │
│   (React)   │     │  (Node.js)  │     │   _dados    │     │ (Flask/Python)   │
└─────────────┘     └─────────────┘     │ (PostgreSQL)│     └──────────────────┘
                                        └──────────────────┘
```

## Stack Tecnológica

| Camada | Tecnologia | Diretório | Descrição |
|--------|------------|-----------|-----------|
| Interface | **React** | `frontend/` | Aplicação web responsiva para visualização e interação do utilizador |
| API de consumo | **Node.js** | `backend/` | API REST que serve o frontend e orquestra acesso aos dados |
| Receção de dados | **Flask / Python** | `servicos/` | Serviços dedicados à receção, validação e ingestão de dados externos |
| Base de dados | **PostgreSQL** | `banco_de_dados/` | Persistência relacional dos dados do sistema |

## Estrutura de Diretórios

```
prodinx/
├── frontend/          # Aplicação React
├── backend/           # API Node.js
├── servicos/          # Serviços Flask/Python de receção de dados
├── jsonfiles/         # Pasta quente de importação JSON
├── banco_de_dados/    # Configuração e scripts da base de dados
└── README.md
```

## Base de Dados (PostgreSQL)

A instância local de PostgreSQL é gerida via Docker Compose no diretório `banco_de_dados/`.

### Credenciais locais

| Parâmetro | Valor |
|-----------|-------|
| Utilizador | `postgres` |
| Password | `Cmgv6190!@` |
| Base de dados | `prodinx` |
| Porta | `5432` (PostgreSQL 18 local) |

### Criar e manter a base de dados

```powershell
cd banco_de_dados
.\manter.ps1
```

Este script sobe o contentor Docker, aplica o schema e confirma o estado da tabela `indicadores`.

### Subir apenas o contentor

```bash
cd banco_de_dados
docker compose up -d
```

### Parar a base de dados

```bash
cd banco_de_dados
docker compose down
```

### String de conexão

```
postgresql://postgres:Cmgv6190!@@localhost:5432/prodinx
```

## IA (Claude via AWS Bedrock)

O Prodinx usa o **mesmo padrão de acesso ao Claude do PanelDX**: credenciais AWS + `bedrock-runtime`, sem acoplamento de código entre projetos.

| Variável | Valor padrão |
|----------|----------------|
| `BEDROCK_REGION` | `us-east-1` |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-sonnet-4-20250514-v1:0` |

1. Copie `.env.example` para `.env` na raiz e preencha `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (pode reutilizar as do PanelDX).
2. Instale dependências Python em `servicos/`: `pip install -r requirements.txt`
3. Teste: `python scripts/testar_bedrock.py`
4. Health check: `GET http://127.0.0.1:5000/health/ia`

Módulo reutilizável: `servicos/ai/bedrock_client.py` (`invocar_claude`, `extrair_json_resposta`).

## Desenvolvimento

Cada diretório principal conterá a sua própria configuração e dependências. Consulte o README específico de cada módulo quando estiver disponível.

### Ordem recomendada de arranque

1. **banco_de_dados** — subir o PostgreSQL via Docker Compose
2. **servicos** — iniciar os serviços Flask/Python de receção de dados
3. **backend** — iniciar a API Node.js
4. **frontend** — iniciar a aplicação React

## Requisitos

- [Docker](https://www.docker.com/) e Docker Compose
- [Node.js](https://nodejs.org/) (LTS) — para o backend e frontend
- [Python](https://www.python.org/) 3.10+ — para os serviços Flask
