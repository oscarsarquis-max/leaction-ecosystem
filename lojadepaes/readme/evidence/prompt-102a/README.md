# Adendo 102A — WhatsApp existente e margem da agenda (24/10/2026)

## Mapa do canal

| Elo | O que existe |
|---|---|
| Entrada na home | Faixa «Fale com A Loja», link «Converse pelo WhatsApp» |
| Código | `frontend/src/components/HomeContact.tsx`, constante no componente |
| Número e papel | `5585999831861`, atendimento público. O cliente abre a conversa |
| Mecanismo | `https://wa.me/5585999831861`, sem `text=`, nova aba. Não envia mensagem sozinho |
| Ambiente | Publicado desde o prompt 61 (`prod-20261001h`) e ainda presente em `prod-20261024b` |
| Evidência | `readme/evidence/prompt-61/` e o pacote atual `/assets/index-aOqExcx5.css` |

O ActionHub tem outro link `wa.me`, de contato comercial de outros produtos. Também é manual e não é remetente da Loja.

No runtime de produção as variáveis de canal encontradas são de e-mail e SES. Não há nome de variável de WhatsApp, Twilio, Meta, Z-API ou equivalente. Não há fila, webhook nem worker de envio. A outbox do prompt 102 registra a ausência do adaptador e não dispara. O e-mail operacional não foi duplicado. Nenhum pedido histórico foi reenviado.

O atendimento por WhatsApp existe. O envio automático de alertas ainda não foi encontrado. Um link não envia alerta para o próprio número.

## Margem

A seção da agenda ficava fora do miolo administrativo e encostava na borda. Agora o conjunto título, calendário e lista usa `width: min(1100px, 100%)`, centralizado, com 20 px laterais no desktop e 16 px até 720 px. O espaço entre calendário e lista permanece. Sem rolagem horizontal nas larguras medidas.

Captura isolada, não a tela autenticada de produção:

| Largura | Antes | Depois |
|---|---|---|
| 1280 | título em 0 px | título em 110 px; lista a 110 px da borda direita |
| 390 | título em 0 px | 16 px dos dois lados; coluna |
| 320 | título em 0 px | 16 px dos dois lados; sete colunas; sem rolagem horizontal |

Arquivos: `agenda-before-1280.png`, `agenda-after-1280.png`, `agenda-after-390.png`, `agenda-after-320.png`.

## Versão

| Item | Valor |
|---|---|
| Imagem | `lojadepaes:prod-20261024b` |
| Rollback | `lojadepaes:prod-20261024a` |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261024T233943Z.sql.gz` (101906 bytes) |
| Alembic | `f9c2a6e81b04`, sem revisão nova |
| Prova no aparelho | não feita; nenhuma mensagem real foi enviada |
