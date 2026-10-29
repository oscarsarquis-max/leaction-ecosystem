# Logística, qualidade e parceiros

29/10/2026. Comparação para decisão. Nenhum modelo foi selecionado no código. Números de temperatura e validade não são fixados aqui.

## Três modelos

| Modelo | O que favorece | O que precisa provar | Quem responde se o pão está pronto e o componente não chegou |
|---|---|---|---|
| Consolidação na Loja | Um lugar para receber, conferir e despachar. Melhor visibilidade para o piloto | Espaço, equipe, armazenamento compatível, janela de chegada, custo parceiro → Loja | A Loja, na conferência, segura o kit |
| Consolidação no parceiro ou ponto dedicado | Pode encurtar deslocamento em alguns bairros | Custódia do pão fora da Loja, padrão de conferência e qualidade | O ponto de consolidação, com regra escrita |
| Coleta em vários pontos pelo transportador | Pode evitar estoque central em alguns pedidos | Roteiro, sincronia, segregação e conferência de todos os volumes antes da casa do cliente | O transportador não entrega o conjunto incompleto; a Loja decide a exceção |

Não escolher pelo menor frete. Comparar tempo total, janela, perecibilidade, falha, custo por kit e pico. A recomendação de piloto, consolidação na Loja, está em [decisoes-para-ratificacao.md](decisoes-para-ratificacao.md) e ainda depende do proprietário.

## Volumes

Cada componente embalado é um volume identificado: composição vendida, produtor, quantidade, unidade e a marca visual da Loja no rótulo. A conferência compara os volumes com a versão vendida. Recebimento parcial fica registrado e não libera a entrega. Troca de custódia registra quem entregou e quem recebeu. Prova de entrega do kit só existe quando todos os volumes do conjunto foram entregues juntos.

Pão e acompanhamento refrigerado não compartilham acondicionamento por presunção. Conservação, validade, identificação e recebimento dependem do alimento real e do responsável técnico. A cartilha da Anvisa trata preparo e transporte nas boas práticas; a aplicação ao estabelecimento e às regras locais precisa ser confirmada. [Referência](https://bibliotecadigital.anvisa.gov.br/jspui/handle/anvisa/225).

## Composição

Para cada unidade vendida, a versão guarda: pão, componentes, quantidades, unidades, rendimento, perda prevista, embalagens, instruções e responsáveis. A quantidade de kits não é a quantidade de pães. Um pão que rende várias porções reserva essa capacidade, não um pão inteiro por kit, quando a ficha disser isso. Perda entra na necessidade de produção e não vira pão fantasma.

Entidades atuais reaproveitáveis como ponto de partida: `Product`, `ProductVariant`, ingredientes e alérgenos, `OrderItem` com snapshot de nome e preço, `physical_units` como unidade física já separada da quantidade comercial. Falta a versão da composição, o produtor e a embalagem. Não há DDL nesta fase. F04 e F05.

## Rastreabilidade

`ProductionBatch` continua sendo a fornada da agenda. Lote sanitário é outro registro: ingrediente ou componente, produtor, validade, recebimento e os kits que o consumiram. Uma ocorrência de qualidade lista os kits ainda não entregues e os já entregues, sem apagar o histórico.

## Admissão do parceiro

Proposta de processo, sem selo automático: cadastro e capacidade; documentos que o jurídico indicar; acordo comercial; aprovação técnica; degustação registrada; publicação autorizada pelo proprietário; avaliação com validade; suspensão; encerramento. Cada etapa tem responsável, evidência e data. Suspensão impede novos compromissos e não apaga os já vendidos.

## Complementaridade

Critérios para ratificar, ainda sem peso aprovado:

| Critério | Eliminaria no piloto? | Como avaliar |
|---|---|---|
| Combina com os pães da Loja | Proposta: sim | Degustação registrada |
| Ocasião de consumo coerente com a Loja | Proposta: sim | Ficha da oferta |
| Diversidade útil, sem repetir o que a Loja já faz | Não, salvo saturação | Curadoria |
| Faixa de preço do kit | Não como corte automático | Comparar com o pão avulso |
| Entrega conjunta viável na janela | Proposta: sim | Ensaio logístico do piloto |
| Regularidade | Depois de dados | Pedidos cumpridos no prazo |

## Marca, receita e imagem

O rótulo comum da Loja convive com cadastro interno do produtor. Expor a marca do parceiro ao cliente é decisão à parte e não foi inferida. Autoria, licença, exclusividade e uso de imagens não estão em contrato lido neste repositório. Não tratar o código como se esses direitos existissem.

## Ocorrências e custo

Quem decide, quem informa o cliente, quem assume o custo e qual registro fica: ver a tabela de falhas em [fluxos-kit-e-estados.md](fluxos-kit-e-estados.md). Custo de frete, desconto, perda e reembolso depois do repasse é decisão econômica (D5).
