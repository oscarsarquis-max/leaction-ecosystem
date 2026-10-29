# Adendo 102B — e-mail e notificação no celular (24/10/2026)

O atendimento manual por WhatsApp continua na home. O envio automático por WhatsApp não foi ligado. O canal novo é Web Push da própria Loja, junto com o e-mail operacional já existente.

## Estado

| Peça | Situação |
|---|---|
| E-mail operacional | configurado, um envio por evento |
| Push no servidor | configurado; chave pública com 87 caracteres; chave privada só no ambiente secreto |
| Inscrição de aparelho | nenhuma |
| Recebimento no celular | não comprovado; nenhum teste foi disparado |
| Worker | `/sw.js` sem cache de página, pedido, pagamento ou sessão |
| Visitante | não recebe pedido de permissão |

A margem da agenda publicada no 102A permanece.

## Como ativar

No Android compatível: entre na área administrativa, toque em **Ativar notificações neste aparelho** e permita. Se a permissão estiver bloqueada, libere as notificações da Loja nas configurações do site.

No iPhone ou iPad compatível: no Safari, Compartilhar, Adicionar à Tela de Início. Abra pelo ícone, entre na área administrativa e só então toque em Ativar. O Safari aberto como página comum não recebe o aviso.

Depois, **Enviar notificação de teste neste aparelho** manda só para esse aparelho, sem e-mail e sem cobrança. A resposta “aceito pelo serviço” não prova que o aviso apareceu na tela.

## Versão

| Item | Valor |
|---|---|
| Imagem | `lojadepaes:prod-20261024c` |
| Rollback | `lojadepaes:prod-20261024b` |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261025T001419Z.sql.gz` (101900 bytes) |
| Alembic | `c4d8e1f07a22` |
| Testes locais | 3 do 102B e as regressões 102, 101, 100 e 72 |
| Captura | isolada, `push-1280.png`, `push-390.png`, `push-320.png`; sem sessão administrativa publicada |
