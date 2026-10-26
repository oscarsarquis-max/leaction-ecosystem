# ISA — Conexão e custo fixo por pedido

26/10/2026. A pessoa não vê tela nova. O pedido deixa de abrir uma conexão, migrar e reler o livro de exclusões. Os números, as regras e o schema 9 permanecem.

## Investigação

`store.connect()` migrava e chamava `reapply_erasures()` em toda abertura. `reapply_erasures()` chama `erased_owners()`. Com `ISA_BACKUP_BUCKET`, isso lista `erasures/` no S3, baixa cada objeto e executa `DELETE` nas tabelas de dono. `wsgi_app._connect()` fazia isso em cada pedido, inclusive `GET /api/ready`. `ai.start_worker` repetia o mesmo ciclo a cada 1–5 s.

`read_session()` também chamava `erased_owners()` em todo pedido autenticado. A exclusão imediata já apaga `app_session` em `forget_owner`. A releitura do livro fica no arranque e depois da restauração, e a sessão consulta o conjunto já lido neste processo.

Pontos que chamam `store.connect` ou `wsgi_app._connect`:

| Lugar | Uso |
|---|---|
| `wsgi_app._connect` | cada pedido `/api/*` e `/callback`, e `/api/ready` |
| `prod_serve.py` | uma vez, antes de aceitar pedidos |
| `ai.start_worker` | laço do worker |
| `serve.py` | laboratório SQLite, uma conexão por pedido |
| `scripts/ops/backup-isa.py`, `cloud-backup.py`, `provision-db.py` | cópia ou provisionamento |
| `scripts/ops/restore-isa.py`, `prove-restore.py` | restauração; em seguida `logical_restore` reaplica o livro |
| testes e provas de desenvolvimento | base descartável |

`restore_dir` e `logical_restore` já chamavam `reapply_erasures()` depois de carregar a cópia. Os scripts de restauração passam por `logical_restore`. Isso foi mantido e coberto por teste.

A tarefa `isa` publica **1** réplica (`desiredCount` 1). O Waitress sobe com **4** threads. O papel `isa_app`, em `scripts/ops/provision-db.py`, tem `CONNECTION LIMIT 8`.

`requirements.txt` tinha `psycopg[binary]==3.2.13`. O pool compatível da mesma linha 3.2, disponível no índice, é `psycopg-pool==3.2.8`. A linha 3.3 não foi usada.

Linha de base, antes de qualquer imagem nova, nesta máquina, 30 chamadas sequenciais a `GET https://isa.actionhub.com.br/api/ready`, percentil linear. Todas 200. Não havia `Server-Timing`.

| | p50 | p95 | máximo | mínimo |
|---|---:|---:|---:|---:|
| Ida e volta, 0.6.11 | 1966 ms | 3774 ms | 4476 ms | 1504 ms |

Não havia sessão do proprietário. `/api/home` e `/api/workspace` autenticados não foram medidos.

## O que mudou

| Arquivo | Mudança |
|---|---|
| `server/pgconn.py` | Pool único por processo. `close()` desfaz transação, volta `autocommit` e devolve a conexão. Conexão quebrada é fechada e não volta limpa ao uso. |
| `server/store.py` | `connect(path, bootstrap=False)` só conecta. `bootstrap=True` migra e reaplica. O conjunto de exclusões fica em memória para a sessão. |
| `server/wsgi_app.py` | Pedido e `/api/ready` usam `bootstrap=False`. Erro de banco vira 503. Log da rota e `Server-Timing`. |
| `server/prod_serve.py` | Abre o pool e faz o único bootstrap. Livro ilegível impede o processo de subir. |
| `server/ai.py` | O worker reusa a conexão do pool e não faz bootstrap a cada volta. |
| `server/test_conn_005t1.py` | Os casos pedidos neste recorte. |
| `server/test_prod.py`, `server/test_pg.py` | O HTTP de teste migra uma vez antes do pedido, como o processo de produção. |
| `requirements.txt` | `psycopg-pool==3.2.8`. |
| `VERSION` | `isa-piloto 0.6.12`. |
| `documents/ISA_CONTINUIDADE_PRODUCAO.md` | 0.6.12 não cria schema e não altera dados. |

O SQLite de laboratório continua com conexão por pedido e migração, sem pool.

## Pool

`min_size` 1. `max_size` 6. Espera de 5 s.

6 = 4 threads do Waitress + 1 conexão retida pelo worker de IA + 1 folga. Uma réplica. O limite do papel é 8, então a cópia agendada ainda consegue uma conexão fora do pool. O timeout do pool responde 503 em vez de crescer sem limite.

## Testes

`python -m unittest discover -s server -p "test_*.py"`: **77 testes, OK**, inclusive `test_pg`, `test_prod`, `test_accounts` e `test_conn_005t1`, no PostgreSQL local `127.0.0.1:5442`. Não é a base publicada.

`node prototype/calc.test.mjs`, `bb-statement.test.mjs` e `lotes.test.mjs`: OK.

O cenário de 26/10/2026 (disponível R$ 1.200, falta de R$ 150 em 28/10, fechamento R$ 1.350, reserva R$ 200, margem de hoje R$ 0, conta do Banco do Brasil R$ 1.000) passou de novo em `test_reference_scene_comes_through_http_on_postgres`.

## Medição

Mesma máquina, mesmo URL, 30 chamadas sequenciais, percentil linear. Depois da 0.6.12.

| | p50 | p95 | máximo |
|---|---:|---:|---:|
| Ida e volta, 0.6.11 | 1966 ms | 3774 ms | 4476 ms |
| Ida e volta, 0.6.12 | 485 ms | 572 ms | 578 ms |
| `Server-Timing` `app;dur`, 0.6.12 | 0,7 ms | 0,8 ms | 0,8 ms |

O que saiu do pedido foi o custo dentro do processo. A ida e volta que resta, cerca de meio segundo, é o caminho desta máquina até o balanceador. Não havia sessão para repetir `/api/home` e `/api/workspace`.

## Log ocioso

Tarefa `9fcc1fee7a8142e883a08d8cffd46134`, do arranque em 26/10/2026 17:41:16 UTC até 12,1 minutos depois. 110 linhas.

- `ISA erasure ledger read`: **1**, no arranque.
- `ISA pool min=1 max=6 timeout=5s`: 1, no arranque.
- `ISA AI worker`: **0**.
- `ISA db`: **0**.
- `ISA api`: 107, healthcheck e a medição. Rota sem identificador, sem nome e sem valor.

Não houve nova listagem do livro nem falha de conexão do worker nesse intervalo.

## Publicação

Cópia anterior: `backups/20261026T173749+0000/`, tarefa `e13e4ada999f440fb94a01f8b8c0928f`, saída 0, 31 tabelas, upload verificado. Sem migration.

| | |
|---|---|
| Versão | `isa-piloto 0.6.12` |
| Schema | 9 |
| Commit do código | `527ede57` |
| Imagem | `sha256:851d40a8c9618c8a0ebb0561325f5081a34f2471dcb2ff3420789bd3312f5e08` |
| Tarefa | `isa-web:21` |
| Retorno | `isa-web:20`, versão 0.6.11 |
| ActionFinance | `actionfinance-web:28` |

`/api/home` sem sessão responde 401. `/api/ready` responde `{"ready": true, "schema": 9}`.

## Aceite

| Critério | Resultado | Evidência |
|---|---|---|
| 1. Pedido não migra nem reaplica | Atendido | Teste do `/api/ready` com contador em zero; log de produção com uma leitura do livro, no arranque. |
| 2. Bootstrap único e falha fechada | Atendido | `bootstrap_or_exit` encerra com `SystemExit` se o livro é ilegível. O processo publicado subiu depois de uma leitura bem-sucedida. |
| 3. Restauração reaplica | Atendido | `test_restore_keeps_a_forgotten_person_out` e o teste já existente em `test_pg`. |
| 4. Pool e conexão limpa | Atendido | `max_size` 6, justificado acima. Teste de `ROLLBACK`, `autocommit` e timeout. |
| 5. Erro de banco vira 503 | Atendido | Pool esgotado e `OperationalError` no teste; mensagens já usadas. O log guarda só o tipo. |
| 6. Worker sem bootstrap nem S3 ocioso | Atendido | Teste reusa a conexão do pool. Doze minutos de log sem segunda leitura do livro e sem falha do worker. |
| 7. Log e `Server-Timing` | Atendido | `ISA api GET /api/ready 200 0.7ms queries=1` e cabeçalho `app;dur=0.7`. |
| 8. Suítes e cenário | Atendido | 77 testes OK no PostgreSQL isolado. O cenário de 26/10 permanece. |
| 9. Antes e depois no host | Parcial | `/api/ready`, 30 amostras, tabela acima. Sem sessão, `/api/home` e `/api/workspace` autenticados ficaram de fora. |
| 10. Schema, cópia e versão | Atendido | Schema 9, cópia verificada, 0.6.12 em `isa-web:21`, retorno `isa-web:20`. |

## Limitações

Não houve sessão do proprietário. A medição autenticada não foi feita. A ida e volta publicada ainda inclui a rede até a região do serviço; o tempo interno do `/api/ready` é o que caiu para menos de 1 ms. Isso não mede o clique completo no navegador, com a página e as consultas do Início. O laboratório SQLite não usa o pool.
