# Gestão — Loja de Pães

Aplicação interna de gestão da padaria. **Separada da Loja**: código, banco (`gestao`), contêiner e login próprios.
Só **lê** a Loja (papel `gestao_reader`, SELECT por coluna, sem dados pessoais) e nunca escreve nela.

- `backend/` FastAPI + SQLAlchemy 2 + Alembic (banco `gestao`), login argon2 + sessão HMAC em tabela.
- `frontend/` React + Vite (shell do backoffice da Loja, identidade verde própria).
- `database/` Alembic do banco `gestao` (a Loja tem o dela; nunca misturar).
- `deploy/` SQL de papéis/grants, compose de produção, scripts do host, bloco do Caddy.
- `docs/` retornos, bloco do Caddy (`docs/caddy/gestao.caddy`) e evidências.

## Desenvolvimento

```powershell
# backend (precisa de Postgres local; os testes criam gestao_test e lojadepaes_test na porta 55440)
cd backend; python -m venv .venv; .venv\Scripts\pip install -e .[dev]; .venv\Scripts\pytest -q
# frontend
cd frontend; npm ci; npm run dev   # :5185, proxy /api -> :8090
```

## Usuários

A senha nunca é argumento nem fica gravada: o comando lê da entrada padrão.

```bash
docker exec -i gestao-api python -m app.cli criar-usuario --usuario NOME --nome "Nome" --papel dono   # dono | operador | somente_leitura
docker exec -i gestao-api python -m app.cli redefinir-senha --usuario NOME
docker exec    gestao-api python -m app.cli listar-usuarios
```

## Publicação e rollback

Ver `docs/retornos/GESTAO-002-retorno.md`. Resumo: `deploy/remote-deploy.sh`, `deploy/caddy-add.sh`; rollback com `deploy/rollback.sh`.
Regra permanente: nada na Loja é alterado sem autorização explícita do Oscar.
