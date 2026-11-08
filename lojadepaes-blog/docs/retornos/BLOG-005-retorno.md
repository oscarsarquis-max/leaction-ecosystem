# BLOG-005 — Retorno

Data: 08/11/2026. O Caddy passou a ler o arquivo do host. A porta 22 do Lightsail ficou sem regras. Nada foi alterado no repositório da Loja, nem em `infra-api-1`, `infra-db-1`, `gestao-api` ou `lepain`. As portas 80 e 443 não foram mexidas.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Backups | **Feito.** |
| 2 | Três sites em 200, queda, `StartedAt` só no Caddy | **Feito.** Queda de cerca de 3,4 s. |
| 3 | Inode igual e scripts corrigidos | **Feito.** Inode `329139` nos dois lados. |
| 4 | Causa e proposta | **Feito.** Nada foi aplicado na Loja. |
| 5 | Porta 22 sem regras | **Feito.** 30 regras fechadas. 80 e 443 seguem abertas. |
| 6 | Este retorno, commit e push | **Feito** neste commit do blog, e no commit dos scripts da Gestão. |

## 1. Backups

Pasta `/opt/lojadepaes-blog/backups/blog-005-20261108T174428Z/`.

| Arquivo | Bytes |
|---|---|
| `Caddyfile.host` | 1123 |
| `Caddyfile.tmp` | 1123 |
| `caddy-adapt.json` | 2834 |
| `caddy-admin-config.json` | 2834 |
| `docker-compose.infra.yml` | 1614 |

O `caddy adapt` da cópia que estava em `/tmp/Caddyfile.full` e o `GET /config/` da API admin deram o mesmo tamanho. O Caddyfile do host já era igual a essa cópia: Loja, Gestão (`>>> gestao` … `<<< gestao`) e LePain (`>>> lepain` … `<<< lepain`).

## 2. Antes e depois

Antes, os três em 200. `StartedAt`:

| Contêiner | Antes |
|---|---|
| `infra-caddy-1` | `2026-09-20T18:14:25.281181575Z` |
| `infra-api-1` | `2026-11-04T16:05:11.35453791Z` |
| `infra-db-1` | `2026-09-20T18:14:08.677061212Z` |
| `gestao-api` | `2026-11-07T15:12:10.777531884Z` |
| `lepain` | `2026-11-08T17:17:43.118284911Z` |

A validação montou o Caddyfile do host num `caddy:2` descartável: `Valid configuration`.

O `docker compose` do arquivo da infra não abre com o usuário `ubuntu`: `open /opt/lojadepaes/secrets/app.env: permission denied`. O `sudo` pede senha. O Caddy foi recriado com a definição só do serviço `caddy`, no projeto `infra`, sem `--remove-orphans`:

```
docker compose -p infra -f /tmp/blog005-caddy-only.yml up -d --no-deps --force-recreate caddy
```

Mesma imagem `caddy:2`, portas 80 e 443, volumes `infra_caddy_data` e `infra_caddy_config`, rede `infra_default`. O Compose avisou que `infra-api-1` e `infra-db-1` ficaram de fora do arquivo temporário e não os removeu.

Início `2026-11-08T17:46:46Z`. Na primeira leitura os três ainda não conectavam. Em `2026-11-08T17:46:49Z` os três responderam 200. A queda medida foi de 3370 ms. A volta automática não foi usada.

Depois, da máquina local: Loja, Gestão e `https://lepain.lojadepaes.com.br/pt` em 200.

`StartedAt` novo só no Caddy: `2026-11-08T17:46:46.938554147Z`. Os outros quatro permanecem os da tabela acima.

## 3. Inode e scripts

```
host inode=329139
container inode=329139
```

`caddy-add.sh` e `caddy-remove.sh` da Gestão e do LePain agora:

- montam o arquivo novo e gravam com `cat novo > Caddyfile`;
- não usam `mv`, `sed -i` nem a cópia em `/tmp` dentro do contêiner;
- validam e recarregam `/etc/caddy/Caddyfile`;
- param, sem alterar nada, se o inode do host e o do contêiner forem diferentes.

As cópias em `/opt/lojadepaes-gestao/deploy/` e `/opt/lojadepaes-blog/deploy/` são essas. Não contêm `/tmp`.

## 4. Causa

O contêiner antigo, no ar desde `18:14:25` de 20/09, segurava o inode `302681` (`nlink` 0, última escrita `18:24:04`). O arquivo do host é o inode `329139`, nascido em `2026-09-20 18:24:06`, dois segundos depois.

Na mesma pasta, `docker-compose.prod.yml` (inode `302682`) e `backup-pg.sh` (inode `302683`) nasceram às `18:11` e não foram trocados. Só o `Caddyfile` ganhou outro inode naquela tarde. `/opt/lojadepaes/app` não é um checkout git. `bootstrap-lightsail-host.sh` não cita o `Caddyfile`. Os deploys da Loja, do `p75` ao `p109f`, recriam só o `api` e usam `sed -i` no `.env` (o `.env` atual nasceu em 04/11 por isso). Nenhum deles copia o `Caddyfile`. O journal das `18:24` mostra a sessão do usuário `ubuntu` encerrando às `18:24:17`, não um cron.

A troca foi a substituição daquele arquivo, com o Caddy já no ar, na subida de 20/09. O comando exato não está num script do repositório. O efeito é o de um `scp`/`sftp` que grava e renomeia, ou de um `sed -i`: o caminho passa a apontar para outro inode e o contêiner continua no antigo.

O próximo deploy no formato desses scripts não sobrescreve o `Caddyfile` e não apaga a Gestão nem o LePain. O `Caddyfile` do git da Loja tem só a Loja. Copiar esse arquivo para o host apagaria os dois blocos. Isso não foi feito.

Proposta, sem aplicar: no `Caddyfile` da Loja, `import /etc/caddy/sites/*.caddy`, com o diretório `sites/` montado no lugar do arquivo único. A Gestão e o LePain passariam a deixar `gestao.caddy` e `lepain.caddy` nessa pasta. Um arquivo novo aparece no montar de diretório sem trocar o inode do arquivo principal.

## 5. SSH

Havia 30 regras na porta 22. As 29 que não eram desta sessão foram fechadas primeiro. A regra `189.14.180.206/32` foi a última. `get-instance-port-states` ficou só com:

| Porta | Estado |
|---|---|
| 80 | aberta, `0.0.0.0/0` e `::/0` |
| 443 | aberta, `0.0.0.0/0` e `::/0` |

Não há regra na porta 22.
