# CURSOR-027-C2D — Diagnóstico seguro (opção C)

| Campo | Valor |
|---|---|
| Status | **CONCLUÍDO — diagnóstico offline + fechamento de acesso** |
| Data | 2026-08-28 |
| Decisão | Opção **C** (diagnóstico; sem retry bootstrap; sem C3) |
| Imagem vulnerável | `DO_NOT_RUN` — ver abaixo |
| Imagem diagnóstica ECS | **não executada** (sem base CRITICAL=0 autorizada nesta passagem) |
| Mutações SQL nesta passagem | **nenhuma** |

## 1. Congelamento

| Controle | Evidência |
|---|---|
| Tasks bootstrap RUNNING | `0` (`family=panne-db-bootstrap`) |
| Serviço ECS Panne | nenhum no cluster `paneldx-cluster` |
| Task definition `panne-db-bootstrap:1` | **INACTIVE** (deregisteredAt 2026-08-28 ~08:40 BRT) |
| ACTIVE TD `panne-db-*` | lista vazia |
| Imagem / logs / roles / bancos | **preservados** (não apagados) |
| Digest | `sha256:87d4cef31efb840834f842103997b3a50f455b4e434073567013075c5b5da65e` marcado **`DO_NOT_RUN`** |

Tag imutável: `db-bootstrap-027-c2-86374c3908f3`. **Não reutilizar.**

## 2. Causa do gate violado (processo)

1. ECR scan COMPLETE com `CRITICAL=8`.
2. Parser PowerShell do relatório falhou (`charmap` / Unicode `\u2212` em texto do scan).
3. Falha de parse **não bloqueou** o fluxo — task ECS foi iniciada mesmo assim.
4. Correção nesta passagem: `panne/infra/db-bootstrap-c2/scan_gate.py` **fail-closed** + `test_scan_gate.py` (10 testes OK).
5. O parser corrigido **não** foi usado para autorizar retry.

## 3. Causa raiz técnica (bootstrap)

Ordem em `bootstrap.py`:

1. `ensure_role` ×4 → `conn.commit()` (roles efetivadas).
2. `role_attrs_ok` ×4 → `SELECT` **sem** `commit` → conexão fica **INTRANS**.
3. `ensure_database` → `conn.autocommit = True` **com transação aberta**.

Reprodução local (Postgres throwaway, não RDS de negócio):

```text
ProgrammingError("can't change 'autocommit' now: connection in transaction status INTRANS")
```

| Item | Conclusão |
|---|---|
| Instrução que falhou | atribuição `conn.autocommit = True` em `ensure_database` (antes de qualquer `CREATE DATABASE`) |
| SQLSTATE (semântica PG) | **25001** (`active_sql_transaction`) — típico ao alterar características de sessão com txn aberta; no psycopg3 o erro pode ser client-side sem `sqlstate` populado |
| `CREATE DATABASE` em transação? | **Não chegou a executar** |
| Autocommit na falha? | Tentativa de ligar autocommit **falhou**; conexão ainda em modo transacional |
| `with connection` | `with connect(...) as admin` abre conexão; SELECTs sem commit abrem/deixam txn implícita |
| Efetivado antes do exit 2 | secrets lidos; `actionhub_prod` visto intacto; **4 roles CREATE + commit**; attrs validados em SELECTs |
| Não efetivado | `CREATE DATABASE panne/panne_demo`; GRANTs; harden schema; isolation; `PutSecretValue` syncStatus |

Handler genérico mascara detalhe: `ERROR: unhandled ProgrammingError` → exit **2**.

## 4. Estado parcial (inferência forte + logs)

| Objeto | Estado |
|---|---|
| `panne` | **provavelmente ausente** (CREATE nunca executado) |
| `panne_demo` | **provavelmente ausente** |
| `actionhub_prod` | **intacto** no momento do log |
| Roles Panne (4) | **existem** (CREATE + commit no log) |
| Atributos roles | LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION, NOBYPASSRLS |
| ACLs CONNECT em DBs Panne | N/A se DBs não existem |
| Schemas/objetos Panne | N/A |
| Secrets `syncStatus` | permanece `pending_postgres_role_bootstrap` (LastChanged = C1; sem update C2) |
| TLS | código usa `sslmode=require`; validação `SHOW ssl` **não** chegou a correr na task falha |

Consulta ECS read-only ao catálogo RDS **não** foi feita: exigiria imagem diagnóstica com scan CRITICAL=0; base bookworm atual da família vulnerável não foi reutilizada.

## 5. Vulnerabilidades ECR

Ver [CURSOR-027-C2D-VULNERABILIDADES.md](CURSOR-027-C2D-VULNERABILIDADES.md) e `_c2-critical-findings.json` (8 CRITICAL nomeados após paginação).

## 6. Fechamento de acesso (obrigatório)

| Ação | Resultado |
|---|---|
| Revogar inbound bootstrap SG → RDS SG | **OK** — removido `sgr-…` de `sg-0c7a0ce1c81ed4cf6` |
| Inbound RDS restante | apenas prod/demo Fargate SGs (`sg-0b4dcda30650d419e`, `sg-0f41648d1720bca80`) |
| Remover master secret da task role | **OK** — policy só `panne/prod|demo/db/*` + logs |
| Comprovar ausência `rds!db-` na policy | **true** |
| Roles/bancos parciais | **intactos** |
| Secrets pending | **mantidos** |
| Imagem/logs/docs | **preservados** |

Passagem futura B1 poderá reabrir acesso com nova autorização.

## 7. Plano de recuperação (não executado)

### B1 — corrigir imagem + retomar idempotente

1. Nova imagem base com scan COMPLETE e **CRITICAL=0** (fail-closed).
2. Corrigir `bootstrap.py`: `commit()`/`rollback()` antes de `autocommit=True`; logar `type(exc)`, mensagem sanitizada e `sqlstate` se houver.
3. Roles já existem → caminho `ALTER ROLE` idempotente.
4. `CREATE DATABASE` se ausente; grants/harden; isolation; atualizar syncStatus.
5. Não aceitar CRITICAL; não reusar digest `87d4cef3…`.

### Rollback controlado do parcial

1. Autorização explícita.
2. Reabrir acesso temporário (inbound + master IAM).
3. DROP ROLE das quatro roles Panne (somente se DBs confirmados ausentes / sem ownership).
4. Fechar acesso novamente; secrets continuam pending até novo bootstrap.

## 8. Artefatos de código (não funcionais de retry)

- `panne/infra/db-bootstrap-c2/scan_gate.py`
- `panne/infra/db-bootstrap-c2/test_scan_gate.py`
- `panne/infra/db-bootstrap-c2/test_bootstrap_tx_diag.py`

## 9. Gate solicitado

Escolher **um**:

- **B1** — nova imagem limpa + bootstrap idempotente corrigido  
- **Rollback controlado** do estado parcial de roles  

Não iniciar C3 até gate.
