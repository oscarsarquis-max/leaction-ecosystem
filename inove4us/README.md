# inove4us · Innovation Desk

Plataforma de inovação colaborativa que conduz o usuário pelas **5 fases do
Design Thinking** (Empatia, Definição, Ideação, Prototipação e Teste) com o
apoio de um agente de IA, baseado na metodologia de Andrea Filatro.

## Estrutura do projeto

```
inove4us/
├── frontend/    # React + Vite + Tailwind CSS (UI / Innovation Desk)
├── backend/     # API Flask (ponte entre o frontend e a IA)
├── services/    # Lógica de IA (DesignThinkingAgent + prompts)
└── database/    # Modelos SQLAlchemy + SQLite (inove4us.db)
```

## Pré-requisitos

- Node.js 18+ e npm
- Python 3.10+

## Como rodar

### 1. Banco de dados

```bash
pip install -r database/requirements.txt
python database/init_db.py
```

### 2. Backend (Flask · http://localhost:5000)

```bash
pip install -r backend/requirements.txt
python backend/app.py
```

Endpoints principais:

- `GET  /api/health` — status do servidor
- `POST /api/agent/interact` — interage com o agente
  ```json
  { "scenario_id": "empatia", "user_input": "Quero inovar no atendimento." }
  ```

### 3. Frontend (Vite · http://localhost:5173)

```bash
cd frontend
npm install
npm run dev
```

O Vite faz proxy de `/api` para o backend em `localhost:5000`, então basta ter
o backend rodando em paralelo.

## Próximos passos

- Integrar um provedor de LLM real em `services/innovation_agent.py`
  (método `_call_llm`).
- Persistir projetos e histórico de interações usando os modelos de
  `database/models.py`.
