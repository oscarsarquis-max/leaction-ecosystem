# Prompt 102 — pedidos válidos, agenda e alertas (24/10/2026)

A leitura e a marcação rodaram dentro da API publicada. Não houve sessão de navegador administrativa, então não há captura visual em 1280, 390 ou 320. O pacote publicado contém o texto “Pedido usa a data da fornada combinada”.

## Inventário

Nomes exatamente “rastro” ou “oscar”: nenhum. A marcação usou a lista de referências já lidas, não uma regra de nome.

| Referência | Identidade lida antes | Estado | Reserva | Decisão |
|---|---|---|---|---|
| LP42E1CA0A1A | rastro 145 | cancelado | não | fora da operação |
| LP72EC1CB055 | rastro 145 | cancelado | não | fora da operação |
| LP7968212021 | rastro 145 | cancelado | não | fora da operação |
| LP242E207138 | rastro 145 | cancelado | não | fora da operação |
| LP18AE314D6C | rastro 145 | cancelado | não | fora da operação |
| LPB0DA668D3F | oscar sarquis | cancelado | não | fora da operação |
| LP87D4BCF4E1 | oscar s g braga | cancelado | não | permanece; revisão |
| LP23FF6F00E2 | oscar s g braga | concluído | sim | permanece; a reserva não foi liberada |
| SD51A91EFF | oscar s g braga | solicitação encerrada | não | permanece; revisão |

Nenhuma conta administrativa foi apagada. Nenhum pedido foi removido, estornado ou cancelado por esta marcação. As seis referências marcadas já estavam canceladas e não ocupavam o total vigente: ele era 0 antes e continuou 0. Depois, a fila comercial tem 12 registros e a lente “Testes fora da operação” tem 6. As seis some da busca comercial e da agenda; as três de revisão continuam na fila comercial. `LP23FF6F00E2` segue com reserva.

## Agenda de outubro

A data é a fornada combinada (`production_local_date`), no fuso America/Sao_Paulo. Outubro de 2026 tem três pedidos reais, um pão cada, todos no histórico do dia, nenhum em aberto:

| Data | Pedido |
|---|---|
| 2026-10-06 | LP42BF063F0C |
| 2026-10-09 | LP7C58FF0190 |
| 2026-10-23 | LPF891F9E5D1 |

Não há “Sem data definida” em outubro. Os testes marcados não aparecem. O calendário público e a configuração da Agenda não foram alterados.

## Canais

O e-mail operacional efetivo é o endereço já definido na Loja. O espelho do aviso usa a fila existente e não envia um segundo e-mail. WhatsApp permanece desativado: não há provedor oficial, não há destinatário administrativo confirmado e nenhuma mensagem foi enviada. A fila de alertas do proprietário está em zero. O número público da vitrine não foi usado.

Para ativar o WhatsApp falta um número com DDI e DDD, confirmado pelo proprietário, e um canal oficial já autorizado. Sem isso o canal continua desligado.

## Versão

| Item | Valor |
|---|---|
| Imagem | `lojadepaes:prod-20261024a` |
| Rollback | `lojadepaes:prod-20261021e`; as tabelas novas podem permanecer |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261024T231727Z.sql.gz` (101137 bytes) |
| Alembic | `f9c2a6e81b04` |
| Saúde | `GET /api/v1/health` ok; resumo e agenda administrativos anônimos respondem 401 |
| Testes locais | 34 testes: prompt 102 e as regressões 101, 101B, 101C, 100 e 72 |
