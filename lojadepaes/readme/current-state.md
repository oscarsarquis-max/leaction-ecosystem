# Estado atual — Loja de Pães

29/09/2026. Sem senhas, tokens nem URLs internas de banco.

## Produção (Prompt 54)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20260929k` (rollback de app: `prod-20260929j`) |
| Bundle | `/assets/index-CawDosg6.js` |
| API | `GET /api/v1/health` e `/ready` = ok |
| Postgres | Lightsail `lojadepaes-app`; Alembic **`b3f7a1c82e09`** |
| Pedidos / Pix | ligados; 14 pedidos preservados; 0 personalizados no banco |
| Fidelidade | `carimbos-da-casa` ativa |
| Receita em destaque | **Pan con Tomate (Tartine Bread)** — composição do Prompt 52 intacta |
| Aviso à padaria | `LOJADEPAES_MAIL_OPS_TO` ativo para avisos operacionais reais; remetente Loja de Pães `<loja@lojadepaes.com.br>` |

Na vitrine a lista longa de ingredientes abre sem repetir o preview. A revisão `/pedido/novo` usa container de 1080 px e quantidade editável com cotação do servidor. Pedido já enviado continua só leitura. O CTA do Criador só leva ao fechamento. Nome e e-mail são exigidos antes de persistir. Novos avisos administrativos saem pela outbox transacional; skipped antigos não são promovidos. Configuração pronta não prova entrega na caixa.

## Editor

**Produtos → Receitas da semana** — https://lojadepaes.com.br/admin/produtos/receitas

## Desenvolvimento local

| Item | Endereço |
|---|---|
| Frontend Vite | http://127.0.0.1:5175/ |
| API | http://127.0.0.1:5075/ |
| Postgres | 127.0.0.1:5438, banco `lojadepaes` |
