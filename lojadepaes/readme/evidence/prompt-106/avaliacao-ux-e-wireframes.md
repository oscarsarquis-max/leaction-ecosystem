# Avaliação do trabalho administrativo e wireframes

29/10/2026. Avaliação por leitura da interface e das rotas. Não houve sessão autenticada nem cronômetro de operador. Onde não há tempo medido, o campo fica vazio de propósito.

## Navegação atual

Menu: Pedidos, Produtos, Agenda, Fidelidade (`AdminApp.tsx:562–574`). Resumo operacional e agenda de produção aparecem na área de pedidos, não nas outras abas. Produtos abre catálogo, receitas, Gigio, harmonizações e complementos.

Isso cobre a operação de um gestor. Não há fila por função, responsável, prazo e bloqueio. Não há área de parceiro.

## Tarefas de hoje

Perfil único: o usuário administrativo configurado. Passos contados pela estrutura da tela, não por observação.

| Tarefa | Entrada | Passos no código da interface | Ambiguidade | Risco | Saída esperada | Tempo observado |
|---|---|---|---|---|---|---|
| Encontrar pedido | Pedidos | Abrir a lista, usar a lente do resumo | Lente filtra; não mostra responsável | Baixo na operação atual | Pedido aberto | Não medido |
| Ver quem deve agir | Detalhe | Estado e pagamento em campos separados | Não há dono da próxima ação além do único admin | Médio quando houver mais gente | Ação nomeada | Não medido |
| Achar falha de verificação | Detalhe e alerta | Erro no registro; e-mail/push se a falha persistir 90 s | Alerta não foi visto em tela publicada nesta auditoria | Médio | Ocorrência com horário da última consulta | Não medido |
| Aceitar | Detalhe ou solicitação | Ação de confirmar, ou autoaceite no pão regular | Autoaceite não aparece como decisão humana | Médio no kit se for herdado | Pedido confirmado, cobrança liberada | Não medido |
| Planejar produção | Agenda na área de pedidos | Calendário da fornada | Fornada parece lote | Alto se for usado como rastreio sanitário | Capacidade do dia | Não medido |
| Localizar entrega | Detalhe | Modalidade, endereço, ação de confirmar | Não há prova de volumes | Médio | `delivery_confirmed_at` | Não medido |
| Registrar ocorrência | Nota interna | Nota no pedido | Nota não bloqueia entrega | Médio | Texto com autoria | Não medido |
| Corrigir cadastro | Produtos | Formulário do produto | `GET` da lista pode preencher a vitrine (F02) | Alto para auditoria em produção | Produto gravado só na ação explícita | Não medido |
| Publicar conteúdo | Produto, receita, complemento, Gigio | Ações de publicação espalhadas | Complemento parece marketplace de vendedor | Médio de interpretação | Conteúdo publicado | Não medido |
| Consultar histórico | Lente de histórico | Pedidos fora da fila vigente | Entrega confirmada precisa estar separada de pronto | Médio | Registro consultável sem voltar à fila | Não medido |
| Fechamento financeiro | Faixas de pagamento no resumo | Pago, pendente, não calculado | Não há liberado versus repassado, porque repasse não existe | Baixo hoje; alto no kit | Totais com caminho até o registro | Não medido |

Tarefas futuras, sem tela: aceite do componente pelo parceiro, conferência do kit, extrato do parceiro. Não foram caminhadas.

Defeito de navegação distinto de funcionalidade: o resumo não deve ser copiado para todas as abas. Falta de kit e de repasse é funcionalidade ausente, não problema visual. Não houve prova de incoerência de dados em produção nesta data.

## Proposta de informação

Hipótese para prototipar depois da ratificação, não autorização para construir as telas. Áreas: Operação, Produção e logística, Catálogo e qualidade, Parceiros, Financeiro, Administração. O resumo de pedidos permanece em Operação.

Prioridade em cada área: o que vence hoje, quem responde, o que impede. Indicador abre os registros que o compõem. Histórico fica acessível e não mistura com a pendência.

Identidade visual da Loja, rótulos, teclado, foco, confirmação de ação destrutiva, proteção contra clique duplo, conflito de edição e dado desatualizado entram no protótipo. Gráfico não substitui a fila.

O cliente não vê identificador interno do Hub. Teste gerencial não mistura com a fila real. Status financeiro não se escreve como etapa física.

## Wireframes documentais

Dados fictícios. Baixa fidelidade.

### Operação, hoje

```text
Operação
[ 3 exigem ação ] [ 1 verificação financeira ] [ 2 entregas na janela ]
------------------------------------------------
LP-EXEMPLO-01  Kit bruschetta  amanhã 18h
  Falta: componente do parceiro não recebido
  Responsável: consolidação
  [ Abrir ]
LP-EXEMPLO-02  Pão 500g  hoje
  Pago. Produção não iniciada.
  [ Abrir ]
```

### Detalhe do kit

```text
LP-EXEMPLO-01  Composição v3  vendida em 02/11
Cliente: pessoa fictícia
Cobrança: uma, cartão, aprovada. Liberação do provedor: não consultada.
Participação: ainda não exigível (política por ratificar).

Tarefas
  Pão 1 unidade física   Loja     embalado
  Tomate confit 1 pote   Parceiro A  a caminho
Volumes recebidos 1 de 2. Kit não conferido. Entrega bloqueada.
[ Não substituir em silêncio ]
```

### Agenda por unidade

```text
Quinta 05/11
Loja     fornada manhã   capacidade 40 unidades   reservadas 22
Parceiro A  janela 14h-16h   componentes aceitos 8   capacidade informada 12
Consolidação  corte 16h30   kits completos 6   incompletos 2
```

### Recebimento

```text
Esperado: volume PARCEIRO-A / kit LP-EXEMPLO-01
Conferido contra composição v3: pote íntegro, quantidade 1
Custódia: da transportadora fictícia para a Loja
Falta o pão desta composição. Não despachar.
```

### Financeiro

```text
Período fictício
Cobrado do cliente     R$ 86,00   fonte: cobrança do pedido
Participação parceiro  R$ 24,00   regra v3, ainda não exigível
Obrigação paga         R$ 0,00
Divergência            R$ 0,00
[ Abrir os lançamentos ]  não editar saldo
```

### Gestor do parceiro

```text
Organização: Parceiro A
Tarefas de amanhã: 8 componentes
Não mostra endereço do cliente nem extrato da Loja.
[ Aceitar janela ] [ Informar embalado ]
```

Critério de usabilidade, para a etapa de protótipo: a pessoa explica, sem código, o que está pronto, o que falta, quem decide e se o dinheiro já foi repassado. Não foi aplicado agora.
