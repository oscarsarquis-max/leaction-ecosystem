# Vocabulário canônico — estoque e compras

- **local de estoque:** espaço lógico/físico em um estabelecimento.
- **item estocável:** identidade organizacional que aponta para ingrediente e unidade canônica.
- **lote interno:** unidade rastreável recebida ou produzida.
- **lote do fornecedor:** identificação externa preservada como dado.
- **movimentação:** evento quantitativo append-only.
- **saldo físico:** soma das movimentações efetivas.
- **reservado:** quantidade comprometida, ainda fisicamente disponível.
- **disponível:** saldo físico menos reservas ativas.
- **em trânsito:** pedido emitido e ainda não recebido; não compõe o físico.
- **separado:** reservado e associado a ordem/batelada; não é consumo.
- **consumo:** fato de produção que reduz estoque quando postado.
- **retorno:** material devolvido pela produção ao estoque.
- **desperdício/descarte:** saída sem retorno ao disponível.
- **inventário:** contagem física em data e local definidos.
- **ajuste:** movimentação explícita que reconcilia diferença; nunca edição de saldo.
- **FEFO:** sugestão operacional pelo vencimento mais próximo; não é custeio.

Pesagem, separação, consumo e movimentação de estoque são fatos distintos.
