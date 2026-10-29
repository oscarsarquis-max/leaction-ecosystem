# Arquitetura e plano incremental

29/10/2026. Comparação depois do inventário. Sem microsserviço, sem troca de provedor e sem ERP como premissa.

## Mapa atual

Loja (API, workers no mesmo processo, Postgres, front administrativo) → Hub Pay da Loja → Mercado Pago. Catálogo, agenda e fidelidade ficam na Loja. Acompanhamentos leem oferta do Hub e guardam snapshot. Gigio é atendimento, não produção.

## Alternativas de evolução

| Alternativa | Quando se justifica | Custo e risco | Recomendação |
|---|---|---|---|
| Crescer no sistema atual, com organização e tarefas no mesmo banco, regras no servidor | Domínio ainda cabe numa operação e o volume não foi medido como gargalo | Menor migração. Exige não vazar filtro só na tela. Regressão do pedido atual | Adotar para o piloto |
| Componente especializado só do livro financeiro ou da fila, ainda chamado pela Loja | Quando conciliação ou retentativa tiverem medida de atraso própria | Um contrato a mais, operação ainda única | Só depois de F20 |
| Separar serviços por parceiro ou por pagamento | Escala ou equipe que o inventário não mostrou | Mais disponibilidade para operar, mais chance de perder o evento entre sistemas | Não adotar agora |
| ERP ou outro adquirente | Se o modelo fiscal ou a conta do provedor forem incompatíveis | Troca grande, fora desta comparação | Não assumir |

Multi-tenant não é, por si, profissionalização. É a regra de isolamento que F01 exige se o parceiro entrar no sistema.

## Contratos lógicos

Ainda sem endpoint. Todo comando ou evento carrega: organização autorizada, ID estável, versão da regra, chave de idempotência, vínculo ao pedido e ao componente, horário de origem, horário de processamento, pré-condição, resultado, erro recuperável, erro definitivo e compensação.

Compensação não estorna nem cobra de novo sem regra ratificada.

| Comando ou evento | Produtor | Consumidor | Idempotência |
|---|---|---|---|
| Reservar componente | Pedido, após cotação | Capacidade do produtor | pedido + componente + versão |
| Aceitar compromisso | Produção da Loja ou gestor do parceiro | Compromisso do kit | tarefa |
| Informar embalado | Operador do produtor | Consolidação | volume |
| Receber volume | Consolidação | Tarefa e custódia | volume + recebedor |
| Concluir conferência | Consolidação | Entrega | kit + versão conferida |
| Registrar prova de entrega | Logística | Pedido e histórico | kit |
| Confirmar pagamento | Hub, como hoje | Loja | evento do provedor |
| Registrar ajuste ou repasse | Financeiro | Livro | origem + sequência |

Paginação, erro e repetição seguem o mesmo contrato. Produtor e consumidor não compartilham transação de banco enquanto esperam rede.

## Carga

Não medida em produção nesta auditoria. Hipóteses, até o proprietário ratificar: dezenas de pedidos por dia, não centenas por minuto; um parceiro no piloto; um kit com poucos componentes; operadores simultâneos na casa de um dígito. Não são capacidade suportada. Healthcheck e os 36 testes isolados não estabelecem esses números.

Listas, índices, exportação, backup e restauração pontual ficam para o lote que os tocar. Não houve ensaio de restauração.

## Etapas

O que pode andar em paralelo: leitura fiscal/sanitária das decisões D1–D6, e o desenho do livro, desde que não escolham o modelo tributário. O que depende de decisão anterior: qualquer prompt de implementação, acesso de parceiro e repasse.

Faixa de esforço, confiança média no diagnóstico de código e baixa na imagem da Loja e na conta do provedor. Engenharia separada de contrato, habilitação e parecer.

| Etapa | Objetivo | Entrada | Saída | Depende de | Risco se pular | Aceite | Parar se | Esforço |
|---|---|---|---|---|---|---|---|---|
| 0 Auditoria | Inventário e decisões | Código e execução acessível | Este pacote | — | Construir em cima de lacuna errada | Este documento entregue | — | Feita |
| 1 Modelo operacional e comercial | Kit, logística, qualidade, quem vende | Diagnóstico e as decisões D1–D8 | Ata de ratificação e pendências externas | Etapa 0 | Código escolhe o fiscal | Proprietário assina as opções; pareceres listados | Faltar vendedor ou consolidação | Pequeno, sobretudo decisão |
| 2 Viabilidade financeira e técnica | Conta do provedor, livro, isolamento | D2, D3, D5 e documentação oficial | Prova em ambiente isolado ou decisão de não usar split | Etapa 1 | Prometer 1:N indisponível | Alternativa escolhida sem função comercial inexistente | Conta sem resposta e sem plano B | Médio |
| 3 Backoffice proposto | Protótipo com dados fictícios | Etapas 1 e 2 | Tarefas por perfil cumpridas em revisão | 1 e 2 | Telas sem regra | Operador explica a exceção | — | Médio |
| 4 Plano de implementação | Lotes, legado, publicação, retorno | Etapa 3 aprovada | Primeiro lote escrito no padrão abaixo | Aprovação explícita | Codar decisão pendente | Proprietário aprova o lote 1 | — | Pequeno |
| 5 Fundação e piloto | Um kit, um parceiro, janela limitada | Lote aprovado | Metas de qualidade, entrega e conciliação | 4 | Abrir acesso geral | Sem vazamento e sem duplicar dinheiro | Meta não atingida | Grande |
| 6 Expansão | Mais parceiros e kits | Medição do piloto | Capacidade sustentada | 5 | Crescer sem número | Evidência de carga | — | Indefinido até medir |

Preservação futura de migração: IDs, valores, datas, autoria e sentido dos estados. Pedido cancelado ou finalizado não vira entregue. Ativação do kit fica restrita. Recuperação não restaura dado antigo por cima de compra nova.

## Padrão do próximo prompt de implementação

Só depois da etapa 4. Cada prompt traz: base exata da imagem e dos hashes; objetivo; escopo e exclusões; decisões já aprovadas; invariantes; dados e estados; permissões; APIs e eventos; interface; falhas; compatibilidade; migração; testes e regressões; evidências; publicação; monitoramento; retorno; conclusão.

O prompt da etapa 1 não manda codificar. Especificação:

- Objetivo: fechar D1 a D8 com opção, recomendação aceita ou recusada, consequência e responsável.
- Base: este pacote e o plano de 29/10/2026.
- Escopo: atas, fichas do kit fictício, matriz logística preenchida com a realidade do endereço e da equipe. Sem migração.
- Exclusões: deploy, conta de parceiro, cobrança, contato com o Mercado Pago em nome do proprietário salvo se o proprietário o fizer, DDL.
- Saída: decisões marcadas como ratificadas ou ainda externas (fiscal, sanitário, provedor).
- Conclusão: dá para escrever a etapa 2 sem inventar vendedor, consolidação ou split.

## Publicação

Esta fase não publica e não retorna versão. O plano de publicação e rollback entra nos lotes futuros, depois de ratificados.
