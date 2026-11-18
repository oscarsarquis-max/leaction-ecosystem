# GESTAO-002 — Retorno

Data: 02/11/2026. Branch `feat/gestao-002-esqueleto`. Gestão no ar em https://gestao.lojadepaes.com.br.

## Resumo

| Verificação | Resultado |
|---|---|
| `https://gestao.lojadepaes.com.br` abre o login; login funciona | 200, login com o usuário `oscar` (dono) funcionando |
| Gestão `/api/v1/health` e `/ready` | 200; `/ready` = `{"gestao_db":true,"sessao":true,"loja_leitura":true}` |
| Hoje mostra a demanda | Mostra **0 pães / 0 fornadas**, e isso é o dado real: a Loja tem só pedidos `cancelled` (8) e `completed` (13) |
| `https://lojadepaes.com.br`, `/api/v1/health`, `/admin` | 200 antes e depois do reload do Caddy (`www` responde 301, como antes) |
| Arquivos em `C:\Projetos\lojadepaes`, tabelas da Loja, restart da Loja | Nenhum |

## 1. Medição prévia (antes de publicar)

Via `p96-refresh-ssh.ps1`: `free -m`, `df -h /`, `docker stats --no-stream`, `docker network ls`. Passou no critério (memória disponível > 500 MB e disco livre > 3 GB), então a publicação seguiu. Rede da Loja: `infra_default`.

Depois da publicação (mesma sessão):

- Memória: 1906 MB total, ~985 MB disponível; disco `/`: 22 GB livres (62% usado).
- `gestao-api` 63 MiB / 256 MiB; `infra-api-1` 244 MiB; `infra-caddy-1` 52 MiB; `infra-db-1` 64 MiB.

## 2. O que foi criado

| Item | Detalhe |
|---|---|
| DNS | Route 53, `A gestao.lojadepaes.com.br -> 52.15.107.86`, TTL 300 |
| Banco | `gestao` (dono `gestao_app`) no Postgres da Loja; `REVOKE ALL ... FROM PUBLIC` |
| Papéis | `gestao_app` (limite 10 conexões), `gestao_reader` (limite 5; `default_transaction_read_only=on`, `statement_timeout=15s`, `idle_in_transaction_session_timeout=30s`) |
| GRANTs do reader | `deploy/sql/02-gestao-reader-grants.sql`: SELECT por coluna em `orders`, `payment_records`, `schedule_closures`, `managerial_exclusions (subject_type, subject_id, reversed_at)`; SELECT nas tabelas de catálogo/agenda/produção da seção 2.2. Nenhuma coluna pessoal. Só CREATE e GRANT; nenhuma tabela da Loja alterada |
| Contêiner | `gestao-api`, projeto compose `lojadepaes-gestao`, rede `infra_default`, 1 worker, `mem_limit: 256m`, `cpus: 0.75`, somente leitura + tmpfs, `cap_drop: ALL`. Imagem `lojadepaes-gestao:prod-20261102a` |
| Host | `/opt/lojadepaes-gestao/{deploy,secrets,backups,images}`; segredos em `secrets/app.env` (chmod 600), gerados no próprio host |
| Caddy | Bloco do Gestão acrescentado ao final de `/opt/lojadepaes/app/infra/Caddyfile` (cópia em `docs/caddy/gestao.caddy`); cópia do Caddyfile anterior em `/opt/lojadepaes-gestao/backups/` |
| Backup do Gestão | `deploy/backup-gestao.sh` (pg_dump do banco `gestao`, 14 cópias). Rodado uma vez à mão (1925 bytes). **Cron e envio ao S3 NÃO instalados** (aguardam autorização) |
| Primeiro usuário | `oscar`, papel `dono`. Senha informada em particular no chat; não está em arquivo, repositório nem log do servidor |

### Caddy: achado importante e como foi resolvido

O contêiner `infra-caddy-1` está montado num **arquivo antigo** do Caddyfile: o arquivo do host foi substituído em 20/09 (inode 329139, 617 bytes, LF), mas o contêiner continua vendo o inode 302681 (651 bytes, CRLF), com o mesmo conteúdo. Por isso o primeiro `caddy reload --config /etc/caddy/Caddyfile` respondeu "config is unchanged" e o Gestão não subiu (a Loja não foi afetada).

Com autorização do Oscar (sem restart e sem gravar dentro do contêiner):

1. `docker exec -i infra-caddy-1 caddy validate --config /dev/stdin --adapter caddyfile < Caddyfile-do-host` -> `Valid configuration`.
2. `docker exec -i infra-caddy-1 caddy reload --config /dev/stdin --adapter caddyfile < Caddyfile-do-host` -> ok.
3. Conferência imediata: Loja 200, admin 200, Gestão 200.

**Estado atual:** o contêiner do Caddy continua montado no arquivo antigo (`/etc/caddy/Caddyfile` dentro dele não tem o bloco do Gestão). A configuração em memória vem do arquivo do host (com o bloco). **No próximo restart do Caddy, ele passa a ler o arquivo do host, já com o bloco do Gestão.** Até lá, um `caddy reload --config /etc/caddy/Caddyfile` voltaria à configuração antiga (sem Gestão); esse é o caminho de volta imediato caso a Loja falhe.

## 3. Testes

- Backend: 58 passados (login, papéis, leitura da demanda; banco da Loja de teste com o schema real `e7b3c9a41d06` e os GRANTs reais do reader).
- Frontend: 10 passados (Login, Hoje); lint e build ok.
- Só testes novos; nada da Loja foi executado.
- Produção: login com senha errada mostra a mensagem; login certo entra; Hoje responde.

## 4. Capturas (produção)

`docs/evidence/gestao-002/`: `login-1280.png`, `login-390.png`, `login-erro-1280.png`, `login-erro-390.png`, `hoje-1280.png`, `hoje-390.png`, `menu-390.png`, `capturas.md`.
Checagens 108A: sem rolagem horizontal, barra superior em uma linha, controles >= 44 px (< 960 px) e >= 36 px, anel de foco de 2 px.

## 5. Rollback

No host (`/opt/lojadepaes-gestao/deploy/rollback.sh`):

1. `docker compose -f /opt/lojadepaes-gestao/deploy/docker-compose.prod.yml --env-file /opt/lojadepaes-gestao/deploy/.env down` (para só o Gestão).
2. Remover o bloco do Caddy: `caddy-remove.sh` (apaga o trecho entre `# >>> gestao` e `# <<< gestao`, valida) e recarregar. Como o contêiner está montado no arquivo antigo, recarregar com `docker exec -i infra-caddy-1 caddy reload --config /dev/stdin --adapter caddyfile < Caddyfile-do-host`. Se for preciso, `caddy reload --config /etc/caddy/Caddyfile` volta à configuração antiga.
3. Banco e papéis não são apagados pelo rollback (só se o Oscar pedir): `DROP DATABASE gestao; DROP ROLE gestao_app; DROP ROLE gestao_reader;` (e `REVOKE` nos GRANTs).

## 6. Desvios e pendências (para decisão do Oscar)

1. **Caddy montado em arquivo antigo** (acima). Sugestão: ao reiniciar o Caddy algum dia, ele passa a ler o arquivo do host; nada a fazer agora.
2. **Regra de firewall da porta 22:** abri e fechei o meu IP (duas janelas: `189.14.176.74` e `189.14.180.206`). O segundo já existia na lista antes; ao fechá-lo, ele saiu. Continuam abertas **29 regras /32 antigas** que não são minhas (não mexi). Recomendo revisão.
3. **Cron e S3 do backup do Gestão:** não instalados; dependem de autorização.
4. **`managerial_exclusions`:** concedi só `(subject_type, subject_id, reversed_at)`, o mínimo para o filtro da demanda. O pedido dizia "só `order_id`", mas essa tabela não tem coluna `order_id` (o pedido é `subject_id` com `subject_type = 'order'`); interpretei assim. Sem dados pessoais.
5. **Docker na máquina:** cerca de 20 GB de imagens recuperáveis (achado da 001); não toquei.
6. **Senha do `oscar`:** a primeira senha foi gerada e logo trocada por `redefinir-senha` (a primeira não foi entregue). Recomendo trocar a atual no primeiro acesso: `docker exec -i gestao-api python -m app.cli redefinir-senha --usuario oscar`.
