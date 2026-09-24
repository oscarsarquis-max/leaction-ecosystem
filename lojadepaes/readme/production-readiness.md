# Produção — Loja de Pães (prévia protegida)

Ambiente definitivo para o proprietário cadastrar conteúdo **antes** da abertura pública. Pedidos, pagamentos e solicitações públicas de data permanecem desligados no servidor.

## Endereço

- **HTTPS:** https://lojadepaes.com.br/
- **www** redireciona para o ápice.
- Certificado Let’s Encrypt no Caddy (renovação automática).
- Zona Route 53 `Z04478628VQ84VS1J0YU`: registros A do ápice e de `www`. NS, SOA, TXT `_amazonses` e os três CNAME DKIM **não** foram alterados. Sem MX; não há caixa em `loja@lojadepaes.com.br` nem em `admin@lojadepaes.com.br`.

## Como entrar no editor

1. Abra o e-mail de ativação enviado a **oscar@oscarsarquis.com.br** (autorizado pelo proprietário).
2. Use o link de uso único (válido por **24 horas** a partir da emissão). Abrir o link **não** o consome; só «Salvar senha» conclui.
3. Defina a senha da conta **admin@lojadepaes.com.br** (identificação fixa na tela). O login não cria caixa postal.
4. Depois da ativação, entre pelo acesso compacto do cabeçalho, na própria loja, com esse e-mail e a senha escolhida.

Se o link expirar **antes** da senha ser gravada, um operador com SSH no host pode emitir outro: `sudo docker compose -f /opt/lojadepaes/app/infra/docker-compose.prod.yml exec -T api python -m app.admin issue-activation --force`. Isso invalida o link anterior. Não use `--force` se a conta já tiver senha.

Não há modo local sem senha neste ambiente. `POST /api/v1/admin/local-login` é recusado.

## Onde cadastrar conteúdo

Com a sessão administrativa:

| O quê | Onde |
|---|---|
| Produtos, fotos, preços, ingredientes, rascunho/publicação | `/admin/produtos` e `/admin/produtos/novo` |
| Ordem das **dez** posições da vitrine | painel de vitrine no editor de produtos |
| Agenda (dias, teto de pães, teto de receitas-base, exceções de semana/data) | `/admin/agenda` |
| Pedidos (quando existirem) | `/admin/pedidos` |
| Solicitações de data (quando existirem) | painel correspondente na gestão |

Mídia vai para o bucket S3 da Loja; o Postgres guarda só a chave e os metadados. Preços não configurados permanecem sem valor inventado.

## O que o painel edita — e o que ainda está no código

**Editável no banco / painel:** produtos, variações, composição, fotos de produto, dez slots, agenda (incluindo quarta/sábado, 15 pães e 5 receitas-base iniciais), política `admin_accept`.

**Ainda no frontend (não é CMS completo):** faixa «feito à mão…», título e texto de abertura («O despertar do levain»), selo de fermentação, mural «À nossa mesa», biblioteca do padeiro, textos do rodapé, fotos editoriais versionadas em `/images/`, logo oficial recortada no cabeçalho, composição calendário à esquerda / sugestões à direita / dez slots abaixo.

## Isolamento e persistência

| Recurso | Destino |
|---|---|
| Aplicação | Lightsail `lojadepaes-app`, Ubuntu 24.04, `small_3_0`, `us-east-2a` |
| Proxy | Caddy 2, portas 80/443 |
| API | FastAPI/uvicorn (2 workers), imagem `lojadepaes:prod-*`, SPA em `/app/frontend/dist` |
| Banco | Postgres 16 no mesmo host (Docker, volume `pgdata`), usuário/banco `lojadepaes` |
| Mídia | `s3://lojadepaes-media-253137917703/lojadepaes-media/` em `us-east-2`, acesso público bloqueado; leitura pela API autenticada/autorizada |
| Backup | `s3://lojadepaes-backup-253137917703/lojadepaes-pg/` (gzip, ciclo de 90 dias só nesse prefixo) + AutoSnapshot Lightsail 07:00 UTC |
| E-mail de saída | SES API `us-east-2`, remetente `Loja de Pães <loja@lojadepaes.com.br>` |
| Segredos | `/opt/lojadepaes/secrets/` no host (não no Git) |

Não compartilha RDS, ECS, EC2 do Hub, Inove, School, PanelDX nem QMind.

Migração publicada: head Alembic **`c3a9f0b18d22`**. Banco de produção iniciado vazio (sem `pao-teste-prompt16`, sem pedido local, sem outbox skipped).

## Backup e recuperação

Dump diário (cron 07:15 UTC no host):

```bash
sudo bash -lc 'set -a; source /opt/lojadepaes/secrets/aws.env; set +a; /opt/lojadepaes/app/infra/backup-pg.sh'
```

Primeiro dump: `20260920T181457Z`. Restaurar: baixar o `.sql.gz` do bucket de backup, `gunzip` e `psql` no serviço `db` **depois** de um backup novo do estado atual. Não use dump do Postgres local `:5438`.

Rollback de **aplicação**: carregar a imagem anterior (`lojadepaes:prod-AAAAMMDD`) e `docker compose up -d` sem reverter migração de banco.

## Controles para abrir depois

Nesta fase:

- `LOJADEPAES_PREVIEW_PROTECTION=true` — catálogo, calendário e APIs de vitrine exigem sessão administrativa.
- `LOJADEPAES_PUBLIC_ORDERS_ENABLED=false`
- `LOJADEPAES_PUBLIC_PAYMENTS_ENABLED=false` (webhook ActionHub responde `{status: ignored}`)
- `LOJADEPAES_PUBLIC_DATE_REQUESTS_ENABLED=false`
- ActionHub **não** configurado neste host (URL e secret vazios de propósito).

**1. Vitrine pública (sem venda):** `PREVIEW_PROTECTION=false`. Catálogo e agenda ficam visíveis a visitante anônimo. Pedidos continuam recusados.

**2. Pedidos (depois, autorização explícita):** `PUBLIC_ORDERS_ENABLED=true`. Ainda sem cobrança.

**3. Pagamentos:** `PUBLIC_PAYMENTS_ENABLED=true` **e** secret/URL reais do ActionHub de produção, webhook HTTPS da Loja, origens de retorno. Não copiar o secret local do Hub.

## Operação no host

```bash
cd /opt/lojadepaes/app/infra
sudo docker compose -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.prod.yml logs --tail 80 api
sudo docker compose -f docker-compose.prod.yml exec -T -w /app/database api alembic current
sudo docker compose -f docker-compose.prod.yml exec -T api python -m app.bootstrap_production
```

Health público: `GET https://lojadepaes.com.br/api/v1/health` e `/ready`.

Redeploy: construir a imagem no workspace, `docker save`, copiar para o host, `docker load`, `docker compose up -d`. User-data do Lightsail deve ser executado com **bash** (`infra/bootstrap-lightsail-host.sh`).
