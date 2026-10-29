# Prompt 103 — resumo só em Pedidos e tabela de receitas (26/10/2026)

Capturas isoladas, com o CSS real do admin. Não houve sessão administrativa, edição de receita, destaque, arquivamento, aviso ou pedido.

| Peça | Situação |
|---|---|
| Imagem | `lojadepaes:prod-20261026a` |
| Rollback | `lojadepaes:prod-20261024c` |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261026T211144Z.sql.gz` (104687 bytes) |
| Alembic | `c4d8e1f07a22` (head), sem revisão nova |
| Pacote publicado | `index-rmMKSs5V.js` contém “Pagamento dos vigentes” e “Soma deste recorte”; o CSS contém `admin-recipe-actions` |
| Sessão publicada | não havia; HTTP 200 não comprova o layout autenticado |

Nas capturas isoladas, a página de receitas depois do ajuste não contém o resumo. Título e tabela começam no mesmo eixo. Em 1440 a linha do Bocadillo mede 111 px, contra 163 px na composição anterior. Não houve rolagem horizontal em 1440, 1280, 768, 390 e 320. A tabela de produtos continua com Foto, Nome, Estado, Vitrine, Disponibilidade, Preço e Ações.
