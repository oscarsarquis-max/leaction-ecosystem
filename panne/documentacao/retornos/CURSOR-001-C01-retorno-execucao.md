# CURSOR-001-C01 — Retorno da execução

Data: 2026-08-22. Sem commit, push ou deploy. Sem avanço para CURSOR-002.

## 1. Arquivos alterados

- `panne/backend/pyproject.toml` — `requires-python = ">=3.12"`; Ruff `target-version = "py312"`
- `panne/backend/app/config.py` — URL padrão sem credencial literal
- `panne/backend/alembic.ini` — URL placeholder
- `panne/.env.example` — marcadores `<configure-local-user>` / `<configure-local-password>`
- `panne/README.md` — Python 3.12 mínimo; configuração local do `.env`
- `panne/scripts/dev/start-backend.ps1` — comentário de mínimo 3.12
- `panne/scripts/dev/bootstrap-db.ps1` — comentário de mínimo 3.12
- `panne/documentacao/prompts/CURSOR-001-C01-corrigir-fundacao.md` — prompt integral
- `panne/documentacao/retornos/CURSOR-001-retorno-execucao.md` — adendo apontando esta correção
- `panne/documentacao/retornos/CURSOR-001-C01-retorno-execucao.md` — este arquivo

Nenhum arquivo fora de `panne/` foi alterado nesta correção.

## 2. Versão mínima oficial do Python

`requires-python = ">=3.12"`

Ruff: `target-version = "py312"`. README e scripts declaram 3.12 como mínimo oficial.

## 3. Indisponibilidade local do Python 3.12

Python 3.12 **não foi instalado**. A arquitetura **não** foi rebaixada para 3.11.

O interpretador desta estação continua 3.11.15 (incluindo o `.venv` já criado). As reexecuções de pytest e Ruff desta correção rodaram nesse runtime. **Não há compatibilidade comprovada com Python 3.12.**

O alvo arquitetural permanece 3.12.

## 4. `.env.example` sem credenciais

Confirmado. `PANNE_DATABASE_URL` usa apenas marcadores. Não há `.env` local criado neste diretório.

## 5. Busca por credenciais

Valores literais sensíveis **foram encontrados** na fundação original e **removidos** de:

- `.env.example`
- `backend/app/config.py`
- `backend/alembic.ini`

Nova busca (`password123`, `admin:password` e padrões equivalentes) nos arquivos da Panne (excluindo `.venv` e `node_modules`): **nenhuma ocorrência**.

O script `bootstrap-db.ps1` continua usando o papel administrativo do container `leaction_db` para `CREATE DATABASE` (sem senha no repositório). O README indica ajustar esse papel só no ambiente local.

## 6. Validações

| Item | Resultado |
|---|---|
| Busca Python 3.11 em arquivos de projeto (exceto `documentacao/`) | Só o comentário “Sem fallback para 3.11” em `start-backend.ps1`. Nenhuma declaração de suporte a 3.11. |
| `requires-python` | `>=3.12` |
| Busca de credenciais literais | limpa após a remoção |
| pytest (`panne/backend`, Python 3.11.15) | 1 passed |
| ruff check / format | ok |
| typecheck / build / testes do frontend | **não reexecutados** — nenhum arquivo do frontend foi alterado |
| Alembic / modelo | **não reexecutados** — sem mudança de migração ou schema |
| `git diff --check` | sem erro de whitespace |

Menções a 3.11 em `documentacao/` são históricas (prompt C01 e retorno CURSOR-001).

## 7. Git

`git diff --stat` (arquivos rastreados): apenas os índices já existentes da fundação — `infra/ecosystem-databases.sql` (+1) e `leaction-ecosystem.code-workspace` (+4). Sem alteração adicional nesta correção.

`git status --short`: `M` nesses dois; `?? panne/`; lixo pré-existente intacto (`diario-start.err`, `deps-install-log.txt`, `mp-log-…`, `phanton/database/_lan-sync/`).

A pasta `panne/` inteira permanece não rastreada; o `--stat` não lista os arquivos internos.

## 8. Nenhuma funcionalidade adicionada

Sem tabelas de negócio, autenticação, módulos funcionais, IA ou mudança de contrato de `/health`.

## 9. Outras aplicações

Intactas. Esta correção tocou só arquivos dentro de `panne/`.
