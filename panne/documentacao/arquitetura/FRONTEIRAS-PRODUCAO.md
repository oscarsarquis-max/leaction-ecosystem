# Fronteiras — produção vs estoque, custos, conformidade e marketplace

## Estoque e compras

Produção aponta **consumo e lote informados**. Não baixa estoque sozinha neste desenho. Reserva, inventário e compra são outro domínio que poderá assinar `consumption.recorded` e `material.short`.

## Custos (consumidores futuros, sem implementação)

Eventos que o domínio de custos poderá ler:

- materiais planejados (snapshot);
- materiais consumidos;
- preço e fonte **vigentes no custo**, não na ficha do padeiro (`supplier_item_price` já existe);
- tempo real das etapas;
- uso declarado de equipamento;
- rendimento, perda, descarte, retrabalho;
- quantidade vendável.

Markup, margem e preço de venda **não** entram no chão. `technical_product` não é SKU comercial.

## Conformidade

Alertas (alergênico, versão não vigente) podem constar na ficha. Avaliação `compliance_*` não libera nem cancela ordem. IA não decide.

## Marketplace / Hub

Fora deste domínio. Nenhuma dependência cruzada.

## Execução (ainda fora)

Pesagem real, consumo real, execução de etapa e rendimento real não existem na `0010`. Os estados futuros estão no catálogo.

## Laboratório

`formulation_*`, `trial`, `approval`, `scale_calculation` permanecem no lab. Produção **copia** na liberação; não altera o lab.
