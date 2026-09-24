# Estado atual — Loja de Pães

20/09/2026. Sem senhas, tokens nem URLs internas de banco.

## Produção (Prompt 21)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ — Let’s Encrypt, HSTS, `www` → ápice |
| Frontend | SPA de produção (Vite build) servida pelo FastAPI atrás do Caddy |
| API | FastAPI no mesmo host; `GET /api/v1/health` e `/ready` = ok |
| Postgres | Docker no Lightsail `lojadepaes-app`; head **`c3a9f0b18d22`** |
| S3 mídia | `lojadepaes-media-253137917703` (público bloqueado) |
| Prévia | `preview_protection=true`; catálogo/calendário anônimos = 401 |
| Pedidos / Pix / cartão / data pública | desligados no servidor |
| Login local sem senha | recusado (`local_passwordless=false`, `POST /local-login` = 403) |
| Ativação | e-mail SES enviado a oscar@oscarsarquis.com.br; senha da conta `admin@lojadepaes.com.br` **ainda a definir pelo proprietário** |

Dados comerciais: 0 produtos, 0 pedidos, 10 slots vazios, agenda quarta/sábado · 15 pães · 5 receitas-base, política `admin_accept`. Conteúdo de desenvolvimento **não** foi copiado.

Remetente transacional: `Loja de Pães <loja@lojadepaes.com.br>`. Não há caixa de entrada nesse endereço.

ActionHub de produção **não** foi ligado a esta instância.

## Desenvolvimento local (inalterado)

| Item | Endereço |
|---|---|
| Frontend Vite | http://127.0.0.1:5175/ |
| API | http://127.0.0.1:5075/ |
| Postgres | 127.0.0.1:5438, banco `lojadepaes` |

Pedido de teste `LP128A3BE540` e produto `pao-teste-prompt16` existem **só** neste banco local — não publicar.

## Composição visual (Prompt 20, preservada)

Calendário à esquerda, sugestões/solicitação à direita, dez slots abaixo; header compacto, logo oficial, imagens editoriais aprovadas. Sem redesign neste deploy.
