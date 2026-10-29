# Decisões para ratificação

29/10/2026. Nenhuma destas decisões foi transformada em código. “Recomendação” é proposta desta auditoria. Quem decide está nomeado. Enquanto não houver aceite, não é regra.

## D1. Onde e por quem consolidar e conferir

| Opção | Consequência |
|---|---|
| A. Na Loja, pela equipe da Loja | Um ponto de conferência. Exige espaço, janela e o transporte do parceiro até a Loja |
| B. No parceiro ou num ponto dedicado | Menos um deslocamento em alguns bairros. A custódia do pão sai da Loja |
| C. O transportador coleta os dois e confere | Sem estoque central. Roteiro e segregação mais frágeis |

Recomendação: A no piloto. Evidência necessária: endereço real, quem recebe, horário de corte e o que acontece se o componente não chegar. Responsável pela decisão: proprietário. Depende de olhar sanitário se o recebimento misturar alimentos com exigências diferentes. Detalhe em [logistica-qualidade-parceiros.md](logistica-qualidade-parceiros.md).

## D2. Quem vende ao cliente e qual a relação com o parceiro

| Opção | Consequência |
|---|---|
| A. A Loja vende o kit e compra o componente embalado | Um responsável perante o cliente. Parceiro é fornecedor. Reembolso é da Loja |
| B. Cada um vende a sua parcela, plataforma intermedia | Contratos, autorização de recebimento e risco divididos. Depende de D8 no provedor |
| C. Remuneração extra por receita ou marca, além de A ou B | Só se existir contrato de licença. Não foi encontrado |

Recomendação: A no piloto. A marca na embalagem não escolhe o emissor fiscal. Responsável: proprietário, com contador e jurídico. Evidência: minuta que diga quem emite ao cliente e qual o preço de fornecimento.

## D3. Como calcular a parcela e quando ela vira exigível

| Opção | Consequência |
|---|---|
| A. Preço de fornecimento fechado na versão vendida, exigível quando o volume é conferido na consolidação | Pagamento do cliente não dispara repasse. Atraso do parceiro não gera obrigação |
| B. Percentual do preço do kit, exigível na aprovação do pagamento | Mais simples de calcular e mais cedo do que a entrega do componente. Estorno depois fica difícil |
| C. Split do provedor no momento da captura | Só com a modalidade habilitada. Não é cálculo, é liquidação |

Recomendação: A, registrada em livro, paga pela Loja em ciclo combinado. Não usar C até a conta comprovar. Responsável: proprietário define a base e o momento; financeiro opera. Evidência: uma compra fictícia em que a soma das partes fecha com o total em centavos.

## D4. Aceite conjunto, reserva, expiração, substituição e cancelamento parcial

| Opção | Consequência |
|---|---|
| A. Kit só cobra depois do aceite da Loja e do parceiro; reserva expira sem cobrança; componente essencial cancelado cancela o kit; substituição é ato explícito | Protege o cliente e não herda o autoaceite do pão regular |
| B. Cobrar no envio e cancelar se alguém recusar | Dinheiro entra antes do compromisso. Piora estorno e reserva |
| C. Autoaceitar o kit como o pão regular | O parceiro pode não ter capacidade. Contradiz a avaliação humana do componente |

Recomendação: A. Pão avulso regular mantém o autoaceite atual. Carrinho misto usa A para o kit e não cria segunda cobrança. Responsável: proprietário. Evidência: os casos A05 e A07 escritos com o texto que o cliente recebe.

## D5. Quem financia frete, desconto, perda e reembolso

| Opção | Consequência |
|---|---|
| A. A Loja financia perante o cliente. Perda por falha do parceiro vira ajuste do fornecimento, não desconto escondido. Depois de pago ao parceiro, o estorno ao cliente gera obrigação de devolver | O cliente tem um interlocutor. O contrato de fornecimento precisa dizer a perda |
| B. Cada parte absorve a sua fatia automaticamente | Parece justo e quebra se o dinheiro já saiu ou se o motivo é de um só |
| C. O provedor resolve sozinho via split | Não comprovado e não cobre descarte nem reentrega |

Recomendação: A. Responsável: proprietário e jurídico. Evidência: três casos numerados (atraso do parceiro, cliente ausente, contestação do cartão) com o centavo de cada um.

## D6. O que autoriza publicar um kit

| Opção | Consequência |
|---|---|
| A. Ficha, degustação, alérgenos, embalagem, capacidade, rastreio e validade da avaliação, com suspensão | Publicar deixa de ser só marcar produto disponível |
| B. Publicar como o pão atual, e tratar qualidade fora do sistema | Mais rápido e sem evidência quando houver reclamação |

Recomendação: A, com os cortes eliminatórios ainda sem peso numérico, listados em [logistica-qualidade-parceiros.md](logistica-qualidade-parceiros.md). Responsável: proprietário e curadoria; responsável técnico valida conservação, rótulo e transporte. Evidência: uma ficha fictícia completa antes do primeiro piloto.

## D7. O que cada operador e parceiro acessa

| Opção | Consequência |
|---|---|
| A. Papéis e organização no servidor, parceiro só na tarefa e no próprio extrato, sem endereço do cliente se a Loja consolidar | Atende o piloto sem abrir a gestão inteira |
| B. Mais uma senha do mesmo admin | Não isola. Rejeitada por esta auditoria |
| C. Planilha fora do sistema no piloto | Evita vazamento no software e não deixa trilha. Só como ponte consciente, com prazo para sair |

Recomendação: A antes de qualquer login de parceiro. C pode organizar o primeiro ensaio operacional se o proprietário não quiser acesso no sistema ainda; não substitui A quando o parceiro entrar. Responsável: proprietário. Evidência: os testes negativos de [perfis-permissoes-dados.md](perfis-permissoes-dados.md) escritos e, na implementação futura, falhando fechado.

## D8. Volume, área e janela do piloto

Não há contagem de pedidos por dia nesta auditoria. Não inventar a capacidade.

| Opção | Consequência |
|---|---|
| A. Um parceiro, um kit, uma janela semanal, área que a Loja já entrega, teto de kits igual à menor capacidade informada (fornada pelo rendimento e parceiro) | Dá para medir falha e conciliação |
| B. Vários parceiros no primeiro ciclo | Mais complementaridade e nenhuma linha de base |
| C. Cidade inteira | Logística sem ensaio |

Recomendação: A. O número do teto sai da ficha e da agenda real, não deste documento. Responsável: proprietário. Evidência: uma semana piloto com kits conferidos, entregues e obrigação conciliada em centavos, sem acesso cruzado.

## O que não é decisão de software

- Tratamento fiscal e documento: contador e jurídico.
- Rótulo, conservação, transporte e lote: responsável técnico e regra local.
- Split 1:N na conta: Mercado Pago, se o proprietário pedir a habilitação. Até lá, D3 opção A.
- Abrir a porta SSH da Loja ou reinspecionar a imagem: operação técnica, fora desta fase. F14 permanece até essa leitura sem escrita.

## Próxima etapa

Somente planejamento, etapa 1 de [arquitetura-e-plano-incremental.md](arquitetura-e-plano-incremental.md): o proprietário marca cada opção acima como aceita, recusada ou adiada, e lista o parecer que ainda falta. Sem essa ata, um prompt de implementação não tem base.
