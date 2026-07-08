# LASim - LeAction Simulator

Plataforma de simulação composta por interface visual, API Gateway, microserviços
de processamento pesado e banco de dados PostgreSQL.

## Estrutura do projeto

```
LASim/
├── frontend/               # Interface visual do usuário
│   └── (Arquivos da interface visual)
│
├── backend/                # API Gateway e Regras de Negócio (Node.js)
│   ├── server.js
│   └── package.json
│
├── servicos/               # Microserviços de processamento pesado (Python)
│   └── simulador-montecarlo/
│       ├── app.py
│       └── requirements.txt
│
├── database/               # Scripts de banco de dados (PostgreSQL)
│   └── schema.sql
│
└── README.md               # Documentação geral do LeAction Simulator
```

## Como rodar (resumo)

### Backend (Node.js)

```bash
cd backend
npm install
npm start
```

### Serviço Simulador Monte Carlo (Python)

```bash
cd servicos/simulador-montecarlo
pip install -r requirements.txt
python app.py
```

### Banco de Dados (PostgreSQL)

```bash
psql -U postgres -d lasim -f database/schema.sql
```
