# MAtivas — Mesa de Inovação

> Plataforma web para apoio à aplicação de **Metodologias Inov(ativas) na Educação**.

## Visão Geral

**MAtivas** é uma versão simplificada de uma *mesa de inovação*: um ambiente
digital concebido para apoiar educadores, gestores e equipes pedagógicas no
planejamento, organização e aplicação de metodologias ativas de ensino-aprendizagem.

O escopo conceitual da plataforma baseia-se **exclusivamente** na obra
*Metodologias Inov(ativas) na Educação*, de **Andrea Filatro**, utilizada como
referência única para o vocabulário, os fluxos e as categorizações adotados no produto.

O projeto é desenvolvido em um contexto **acadêmico e de gestão de projetos de TI
avançada**, com ênfase em boas práticas de engenharia de software, separação de
responsabilidades e preparação para implantação em nuvem (**AWS**).

## Stack Tecnológica

| Camada              | Tecnologia                  | Descrição                                                        |
| ------------------- | --------------------------- | ---------------------------------------------------------------- |
| Frontend            | **React** (via Vite)        | Interface web, single-page application.                          |
| Backend / API       | **Flask** (Python)          | API REST e regras de negócio.                                    |
| Banco de Dados      | **PostgreSQL**              | Persistência relacional dos dados da plataforma.                 |
| Serviços externos   | **Python / Node.js**        | Integrações e serviços auxiliares (placeholder).                 |
| Infraestrutura      | **AWS**                     | Hospedagem e provisionamento de ambientes (cloud).              |

## Estrutura de Pastas

```text
MAtivas/
├── frontend/        # Aplicação React (SPA) — interface do usuário
│   └── package.json # Dependências e scripts do frontend
├── backend/         # API REST em Python/Flask
│   ├── app.py       # Ponto de entrada da aplicação (Hello World)
│   └── requirements.txt
├── database/        # Scripts de banco de dados (PostgreSQL)
│   └── init.sql     # Script de inicialização do schema
├── services/        # Serviços externos e integrações (placeholder)
│   └── main.py
└── README.md        # Documentação do projeto
```

| Diretório    | Responsabilidade                                                                   |
| ------------ | ---------------------------------------------------------------------------------- |
| `frontend/`  | Camada de apresentação. SPA em React responsável pela experiência do usuário.      |
| `backend/`   | Camada de aplicação. Expõe a API REST, concentra regras de negócio e validações.   |
| `database/`  | Camada de persistência. Scripts de criação de schema, migrações e dados iniciais.  |
| `services/`  | Serviços auxiliares e integrações com sistemas/APIs externos.                      |

## Pré-requisitos

- [Node.js](https://nodejs.org/) **18+** e npm
- [Python](https://www.python.org/) **3.10+** e pip
- [PostgreSQL](https://www.postgresql.org/) **14+**

## Como Rodar os Ambientes Localmente

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio> MAtivas
cd MAtivas
```

### 2. Backend (Flask)

```bash
cd backend

# Criar e ativar um ambiente virtual
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Linux / macOS
# source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Executar a API
python app.py
```

A API ficará disponível em `http://localhost:5000`.
Endpoints de verificação: `GET /` e `GET /health`.

### 3. Frontend (React)

```bash
cd frontend

# Instalar dependências
npm install

# Executar o servidor de desenvolvimento
npm run dev
```

A aplicação ficará disponível em `http://localhost:5173` (porta padrão do Vite).

> **Observação:** o diretório `frontend/` contém atualmente apenas o `package.json`.
> O scaffold completo do Vite (arquivos `index.html`, `src/`, configuração) pode ser
> gerado com `npm create vite@latest` caso ainda não exista.

### 4. Banco de Dados (PostgreSQL)

```bash
# Criar o banco de dados
createdb mativas

# Aplicar o script de inicialização
psql -d mativas -f database/init.sql
```

## Variáveis de Ambiente

Recomenda-se utilizar um arquivo `.env` (não versionado) para configurar:

| Variável        | Descrição                                  | Exemplo                                        |
| --------------- | ------------------------------------------ | ---------------------------------------------- |
| `PORT`          | Porta da API Flask                         | `5000`                                         |
| `FLASK_DEBUG`   | Ativa o modo de depuração (`1`/`0`)        | `1`                                            |
| `DATABASE_URL`  | String de conexão com o PostgreSQL         | `postgresql://user:pass@localhost:5432/mativas`|

## Roadmap (alto nível)

1. Estruturação do esqueleto do repositório. ✅
2. Modelagem do banco de dados conforme a obra de referência.
3. Implementação dos endpoints da API e das regras de negócio.
4. Desenvolvimento das telas da mesa de inovação no frontend.
5. Configuração de CI/CD e provisionamento de infraestrutura na AWS.

## Referência Conceitual

FILATRO, Andrea. *Metodologias Inov(ativas) na Educação*.
Obra de referência única para o modelo conceitual da plataforma.

## Licença

Projeto de uso acadêmico. Definição de licença a ser confirmada.
