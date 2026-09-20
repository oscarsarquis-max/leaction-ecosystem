# Regras de negócio — decisões e hipóteses

## Adotado nesta base

- Pedido operacional e pagamento são eixos distintos. Confirmar fornada **não** marca pago. Pago **não** conclui o pedido. A confirmação no painel admin é operacional, sem automatismo financeiro.
- Rascunho pode estar incompleto. Confirmação exige itens, compatibilidade ativa, preços configurados, prazo, janela/fornada abertas, modalidade, nome e um contato; endereço estruturado se `delivery`.
- Após confirmar, itens (preço/capacidade) não mudam; o caminho é cancelar. Cancelamento exige motivo e preserva itens, histórico e registros financeiros.
- Capacidade: `holds_capacity`. Concluir atendimento **não** devolve vaga da fornada nem da janela. Cancelar depois de `in_production` também não. Cancelar ainda em `confirmed` libera a reserva.
- Entrega (`delivery`) existe no modelo da janela, mas **não** está disponível comercialmente: sem taxa, cobertura, endereço da loja nem calendário de rotas.
- Compatibilidade é lista explícita. Par ausente = não autorizado à venda.
- Dicas de combinação são editoriais; não bloqueiam compra.
- Pagamentos futuros: provedor interno `actionhub`. Contrato da API do Hub ainda não está acoplado. O painel só consulta registros locais.
- Acesso à gestão: uma credencial de servidor (hash Argon2id + segredo de sessão). Sem isso, admin desligado. Não há contas de cliente nem recuperação de senha.
- Receitas não fazem parte desta etapa; virão do Panne.
- Produtos padrão da vitrine são cadastro próprio (`products` / `product_variants`), distintos do assistente. Publicação exige foto, descrição curta, composição e variação vendável com preço.
- A seleção do cliente no navegador não é pedido: sem ActionHub, sem reserva de fornada e sem total enviado pelo cliente como autoridade.

## Hipóteses a validar antes de vender de verdade

| Tema | Hipótese atual | Risco |
|---|---|---|
| Preços | Seeds e vitrine sem preço (`NULL`) | Confirmação real impossível até configurar centavos |
| Compatibilidades | Seed autoriza todas as massas × inclusões × formatos do protótipo | Pode não refletir produção |
| Alergênicos | Glúten nas massas e oleaginosas em nozes, **não revisados** | Não usar como alegação de segurança alimentar |
| Capacidade | 1 unidade de item = 1 vaga; limite opcional por massa na fornada | Ingrediente/equipamento não modelados |
| Prazo | `now(UTC) <= order_deadline_at` | Calendário da padaria em `America/Sao_Paulo` ainda não aplica feriados |
| Conclusão | `completed` **mantém** `holds_capacity` | Não reabrir vaga da mesma fornada/janela |
| Cancelamento após produção | Mantém `holds_capacity` | Pão pode já ter sido assado; não há devolução automática |
| Pagamento vs reserva | Reserva na confirmação operacional, independente do Hub | Definir se a fornada só reserva após `paid` |
| Imagens | `image_ref` nulo no seed do assistente; fotos de produto padrão em `var/media/` | Backup do diretório de mídia; não misturar com `internal*` |
| Receitas | Fora desta etapa | Integração futura com o Panne |
| Pedido de produto padrão | Fora desta etapa; `order_items` ainda é só pão personalizado | Origem exclusiva e capacidade por unidade produzida, não por embalagem comercial |

Domínio `lojadepaes.com.br` está em transição para a AWS; esta etapa não altera DNS nem publicação.
