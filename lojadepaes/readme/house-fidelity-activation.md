# Carimbos da casa — pacote de ativação

Prompt **44**. A campanha só entra em vigor depois da comprovação isolada, da ausência de lacunas na vitrine e da ativação com `starts_at` no instante do servidor.

## Mapeamento de “fechada e paga”

| Linguagem do proprietário | Evento no sistema | O que não é |
|---|---|---|
| **Fechada** | Aceite administrativo: status `confirmed` (e os seguintes) com `confirmed_at` | Enviar o formulário, abrir checkout, emitir Pix, marcar pronto |
| **Paga** | Pagamento conciliado no servidor (`financial_status=paid` e valor líquido do pão > 0) | Tela do navegador, QR gerado, “verificar pagamento” no cliente |
| **Entrega / retirada** | `fulfilled_at` | **Não entra na pontuação.** Consome crédito de resgate já reservado |

Pontua a combinação **fechada + paga**, na compra feita **durante a campanha ativa** (`created_at >= starts_at`), com participação e sessão verificada no fechamento. O instante de elegibilidade é o mais tardio entre `confirmed_at` e o pagamento conciliado, no fuso `America/Sao_Paulo`.

## Regras em vigor (44)

- Participação opcional. CPF identifica; não autentica sozinho. Compra avulsa sem cadastro/CPF não pontua.
- Nenhuma retroatividade: sem importar histórico, sem vincular compras avulsas depois do cadastro.
- Quatro pedidos válidos no mesmo mês = um crédito; oito = dois. Créditos permanecem na virada; a contagem recomeça.
- Crédito = um pão de 500 g de qualquer tipo da vitrine. Sem teto de R$ 70. Frete separado. Capacidade e aceite continuam valendo.
- Pedido só de presente/frete não pontua. Resgate com total zero não chama Mercado Pago.
- Estorno integral ou cancelamento reverte o carimbo com histórico. Estorno parcial **não decide sozinho**: abre revisão administrativa pendente, não concede crédito novo daquele pedido e não apaga benefício já usado.

## Catálogo de resgate

Um tipo da vitrine é elegível se tiver apresentação ativa de 500 g e uma unidade física. Peso 500 g sem `physical_units` preenchido conta como um pão — é assim que a vitrine já vende. A gestão vê o relatório em `/admin/fidelidade` **antes** de ativar.

## Como ativar

1. Backup verificável do Postgres. Rollback de aplicação = imagem anterior; **não** reverter o banco.
2. Publicar a imagem que passou na jornada isolada.
3. Aplicar só as migrações necessárias (`b2d8f4a91c30`, `c5a1d8e04b27`, `d6b2e9f15c38`).
4. Ligar `LOJADEPAES_HOUSE_FIDELITY_ACTIVE=true` e recriar a API.
5. Chamar `POST /api/v1/promotions/house-fidelity/admin/activate` (sessão admin). Isso grava `starts_at` no instante UTC do servidor. Não reescreve uma campanha já ativa.
6. Conferir peça pública, formulário real, rotas `/me` e `/rewards` protegidas, catálogo e health/outbox. Sem criar cliente, sem SES, sem Pix, sem resgate real.

Não seed, não copiar banco local, não creditar histórico e não enviar divulgação.
