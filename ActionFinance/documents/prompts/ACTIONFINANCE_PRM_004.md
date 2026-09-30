# ACTIONFINANCE_PRM_004 — Recebimentos, pagamentos registrados e contas financeiras

Versão 0.1 — 29/09/2026. Especificação de negócio, UX e dados do analista.

## 1. Entrega e limites

Implemente em C:\Projetos\ActionFinance a próxima fatia local do produto: **registrar recebimentos e pagamentos já realizados, com baixa total/parcial de títulos, conta financeira, extrato gerencial e estorno de registro**. Entregar backend Java, PostgreSQL e telas funcionais em português, aproveitando o PRM_003 aprovado. Não reiniciar a fundação.

ActionFinance é produto autônomo e integrável pela Spider com sistemas internos ou externos. ActionHub permanece o módulo de execução de pagamentos existente; Panne continua a origem de compras/estoque no primeiro cenário do grupo. Este prompt implementa registro manual demonstrativo, sem executar cobrança, Pix, transferência, pagamento ou comunicação externa. Botões não podem sugerir que enviam dinheiro. Não implementar conectores ou exigir sistemas externos para operar.

Primeira jornada: título a receber de R$ 150,00 → registrar recebimento de R$ 50,00 em uma conta → restante R$ 100,00 → registrar restante → título quitado na visão financeira. Uma baixa indevida pode ser estornada contabilmente no controle local, recompondo o restante e gerando movimento inverso. Mesma lógica para contas a pagar, com saída na conta.

Tudo continua local-demo e fictício. Não autorizar produção/piloto, IAM corporativo, conciliação bancária, pagamentos externos, baixas em lote, transferências entre contas, juros, descontos, multas, tarifas, impostos, câmbio, recebimento acima do título ou distribuição de uma baixa entre vários títulos. Esses casos exigem desenho próprio. Não criar telas ou tabelas vazias dessas capacidades.

Leia as instruções locais aplicáveis, PRM_003 v0.3, seu encerramento e documentos ARQ/DOM/DAT/UX. Preserve Java 21, Boot 3.4.2, isolamento, dinheiro exato, idempotência e scripts seguros. Nenhuma alteração em Spider/Hub/Panne, regras globais, configuração global Docker, volumes preservados ou migrations V1–V3 já aplicadas. Sem commit/push/deploy/Git aninhado. Trabalhe somente no ActionFinance.

## 2. Regras financeiras deste recorte

### 2.1 Compromisso, baixa e movimento

São objetos diferentes:

- **Título:** compromisso original com contraparte, competência e vencimento.
- **Baixa (settlement):** registro de recebimento/pagamento que reduz o valor pendente do título.
- **Movimento:** entrada/saída na conta financeira associada à baixa.
- **Estorno do registro:** desfaz o efeito de uma baixa no controle local mediante registro adicional; não devolve dinheiro ao banco nem apaga o original.

Para um título OPEN: realizado = soma de alocações de baixas não estornadas; restante = valor original − realizado. Nunca somar baixas de outra empresa ou as que foram estornadas. A baixa pode ser parcial ou igual ao restante, jamais superior. DRAFT/CANCELLED não recebem baixa. Todos os valores em BRL.

Manter status documental DRAFT/OPEN/CANCELLED. Acrescentar situação financeira **derivada**, sem coluna divergente de saldo: UNSETTLED (realizado zero), PARTIAL (entre zero e principal), SETTLED (restante zero); para DRAFT/CANCELLED, NOT_APPLICABLE. UI usa “Em aberto”, “Parcialmente recebido/pago”, “Recebido/Pago”, conforme direção. OPEN quitado não é vencido. Vencido requer OPEN, restante positivo e due_date anterior à data de negócio.

Nos resumos de compromissos, usar **restante**, e rotular “A receber”/“A pagar” e “Vencidos”. Rascunhos/cancelados ficam fora; quitados não somam pendência. Exibir valor original e restante separadamente na lista. Não manter o antigo total do principal rotulado como pendência depois de uma baixa parcial.

### 2.2 Baixa manual

Exigir título OPEN, conta ativa da mesma empresa/moeda, valor positivo ≤ restante, data efetiva não futura, meio de recebimento/pagamento, observação opcional e versão esperada do título. Data efetiva não pode ser anterior à data de abertura de controle da conta. Permitir pagamento antecipado em relação a competência/vencimento. Datas são dates na zona de negócio da empresa; instantes de registro são UTC. Não usar a data atual de outro fuso para validar.

Meios locais: PIX, BANK_TRANSFER, CASH, CARD, OTHER, apresentados em português. São classificações informativas; escolher Pix não dispara Pix. Conta é genérica, sem exigência de instituição/agência/número de conta ou dados sensíveis. Nenhuma conta externa é consultada.

Cada baixa aloca todo seu valor em exatamente um título e gera exatamente um movimento: entrada para RECEIVABLE, saída para PAYABLE. Transação única: validar/lock, criar baixa e alocação, criar movimento, incrementar versão do título, gravar evento e idempotência. Falha em qualquer etapa reverte tudo.

Após existir qualquer baixa histórica, mesmo estornada, bloquear correções de principal, moeda, direção, contraparte e competência do título neste recorte. Manter correção motivada de descrição, vencimento e categoria. Cancelamento documental é permitido somente com realizado líquido zero. Corrigir um valor já movimentado requer estornar as baixas e cancelar/substituir o título; não alterar fatos históricos silenciosamente.

### 2.3 Estorno do registro

Somente uma reversão integral por baixa neste recorte. Exigir motivo de 3–500 caracteres, data efetiva do estorno entre a data da baixa e hoje, versão atual do título e permissão específica. A reversão referencia a baixa original, gera movimento com sinal oposto na mesma conta e libera seu valor no título. Não editar/deletar a baixa/movimento original.

Se a conta tiver sido inativada, permitir estornar a baixa antiga: inativação impede novas baixas, não correção de histórico. Estorno repetido com a mesma chave retorna o resultado original; outro pedido para baixa já estornada retorna conflito sem novo movimento. Não há “estorno de estorno” nesta entrega: novo fato válido é nova baixa.

O saldo gerencial de uma conta pode ficar negativo: registrar fato não pode ser impedido por ausência de saldo conhecido. Mostrar alerta informativo; não tratar como autorização bancária.

## 3. UX definida pelo analista

Preservar linguagem visual aprovada. Acrescentar **Contas financeiras** à navegação, após A pagar e antes de Cadastros. Não substituir a tela inicial por dashboard. Empresa e demonstração local permanecem visíveis. Apenas contas financeiras da empresa ativa; sem consolidação entre clientes ou empresas.

### 3.1 Título e lista

Na lista: contraparte, descrição/referência compacta, vencimento, valor original, restante e situação financeira/documental. Mobile usa cartões, mantendo restante em destaque. Adicionar filtro financeiro “Com pendência” (padrão), “Parcial”, “Quitado” e “Todos”, aplicado aos OPEN; rascunhos/cancelados continuam acessíveis pelo filtro documental, sem combinação que os esconda inadvertidamente. Ao selecionar DRAFT/CANCELLED, desabilitar e desconsiderar o filtro financeiro com indicação clara. Resumo cobre todo o filtro, não só a página.

Detalhe do título:

```text
Referência · Contraparte                          [situação]
Valor original          Recebido/Pago             Restante
R$ 150,00               R$ 50,00                  R$ 100,00

[Registrar recebimento/pagamento] [Corrigir] [Cancelar título]

Baixas
Data · Conta · Meio · Valor · Situação · [Ver / Estornar registro]

Histórico
Criação, correções, baixa e estorno com autor, data e motivo
```

Em quitado, retirar ação de nova baixa. Em DRAFT/CANCELLED, não oferecer baixa. Para usuário sem permissão, ocultar ações de escrita; backend também bloqueia. Botão de cancelar indisponível com realizado líquido positivo e explicação “Estorne os registros de baixa antes de cancelar este título”.

### 3.2 Registrar recebimento/pagamento

Página dedicada: /receivables/:id/settlements/new ou /payables/:id/settlements/new. Cabeçalho “Registrar recebimento realizado”/“Registrar pagamento realizado”. Exibir contraparte, referência e restante. Texto curto: “Este registro atualiza seu controle financeiro. Não envia nem movimenta dinheiro.”

Campos na ordem: conta financeira pesquisável; valor; data efetiva; meio; observação opcional (até 500). Valor inicialmente igual ao restante; data inicialmente hoje, ambos editáveis e explicitamente visíveis. Não escolher silenciosamente uma conta. Se nenhuma conta ativa existir, oferecer criar conta em diálogo ou página com retorno preservando formulário. Meio começa vazio.

Rodapé: Voltar e Registrar recebimento/pagamento. Um único envio, sem confirmação redundante. Durante envio bloquear repetição. Resultado desconhecido preserva a operação congelada, como corrigido no PRM_003; oferecer Tentar novamente com mesma chave, corpo, alvo, empresa e ator. Conflito por baixa concorrente mostra restante atual e pede revisar valor; não reduzir valor automaticamente.

Sucesso retorna ao detalhe do título, destacando baixa registrada e novo restante. Nunca mostrar “Pix enviado” ou “Pagamento executado”. Validações próximas aos campos, foco no resumo de erros, preservação de entradas e saída protegida.

### 3.3 Estorno

Detalhe da baixa em /settlements/:id: título, conta, data efetiva, valor, meio, registro manual, autor e instante de registro; se estornada, mostrar motivo/data/autor do estorno e referência ao movimento inverso. Botão “Estornar registro” com permissão.

Diálogo modal acessível: identificação da baixa, efeito no restante do título e na conta, data do estorno e motivo. Mensagem: “O estorno corrige o controle financeiro. Nenhuma devolução ou operação bancária será enviada.” Botões Voltar e Confirmar estorno do registro. Manter histórico original visível, marcado Estornado. Controle de foco/Escape e retorno ao contexto conforme o padrão já implementado.

### 3.4 Contas financeiras e extrato gerencial

/financial-accounts lista nome, tipo, situação e **saldo gerencial registrado** em BRL. Tipos BANK/CASH/EIRO: Banco, Caixa físico, Outra. Não usar logotipos de bancos ou indicador “conciliado”.

Criar conta: nome obrigatório, tipo, data de início do controle e saldo inicial informado. Saldo inicial obrigatório, pode ser zero/negativo; nunca assumir zero sem entrada explícita. Explicar: “Informe o saldo no início desse dia. As movimentações registradas a partir dele atualizarão o saldo gerencial.” Data não futura. Após criação, saldo/data iniciais ficam imutáveis neste recorte. Não pedir documento fiscal ou credenciais.

Detalhe /financial-accounts/:id: nome, empresa, moeda, saldo gerencial atual e texto “Calculado a partir do saldo inicial e dos registros locais; não conciliado com o banco”. Permitir renomear/inativar/reativar com versão, sem apagar a conta ou seu histórico. Inativar não zera saldo.

Extrato: filtro por período inclusivo, paginação, data efetiva, descrição/título, tipo de registro, entrada, saída e saldo após movimento. Ordenação ascendente por data efetiva, abertura primeiro no dia de abertura, depois instante de registro e ID. Saldo anterior ao período e saldo final do período calculados sobre todo o conjunto, não por página. Movimento retroativo exige recalcular saldo acumulado; não persistir um running_balance que fique desatualizado. Fora do período, saldo atual continua claramente separado do saldo final filtrado.

Exibir datas efetivas e permitir consultar instante/autor do registro. Um estorno posterior não remove a baixa do extrato de período anterior. Mobile: cartões de movimento, resumo compacto, filtros recolhíveis e nenhum scroll horizontal de página. Controles de formulário com altura mínima 44 px; preservar o restante do padrão PRM_003.

## 4. Estrutura de dados a implementar

Schema actionfinance, UUIDs, tenant_id/company_id obrigatórios nas novas tabelas, FKs compostas para isolamento, ON DELETE RESTRICT. Instantes UTC e dates de negócio. Dinheiro numeric(19,0) na persistência e string de centavos na API; nenhuma conversão para float ou long incapaz de representar o domínio. Soma de movimentos pode exceder limite de uma linha: agregar com precisão arbitrária e validar limites de campos individuais.

Criar migrations incrementais após as já aplicadas. Não editar V1/V2/V3 nem dados históricos para acomodar o modelo. Banco deve assegurar unicidade estrutural; serviço assegura invariantes entre linhas sob locks/transação.

Entidades: financial_account, settlement, settlement_allocation, settlement_reversal, cash_movement, financial_account_history — campos, CHECKs, UNIQUE e FKs conforme especificação do analista (scope tenant+company, imutabilidade de fatos, um título por baixa, uma reversão por baixa, OPENING único por conta).

### 4.1–4.3

Restrições de movimentos, saldo, histórico, concorrência, idempotência e índices conforme seções 4.1–4.3 do prompt do analista. Ações SETTLEMENT_RECORDED e SETTLEMENT_REVERSED no histórico do título por migration incremental. Locks: escopo, idempotência, título, conta.

## 5. API e permissões

Manter /api/v1 e contexto de empresa autorizado resolvido no servidor.

- GET/POST /financial-accounts; GET/PATCH /financial-accounts/{id}; GET /financial-accounts/{id}/movements
- POST e GET /receivables/{id}/settlements e /payables/{id}/settlements
- GET /settlements/{id}; POST /settlements/{id}/reversal
- Título: amountMinor, settledAmountMinor, outstandingAmountMinor, settlementStatus, overdue recalculado

Permissões: financial-accounts:read/write, settlements:read/write/reverse. Operator demo recebe as novas; viewer só leitura.

## 6. Demonstração e testes de aceite

Seed explícito local-demo sem alterar títulos já cadastrados pelo usuário. Contas fictícias e exemplos identificáveis: recebível 150 com baixa 50; obrigação 100 com baixa integral; baixa estornada; conta de outra empresa.

Testes 1–7 do prompt do analista. Maven verify completo; frontend lint/test/build/audit. Backup/restore adaptado.

## 7. Entrega e parada

Salvar este prompt. Registrar encerramento do PRM_003 no índice. Atualizar DOM/DAT/UX. Produzir REV_004. Encerrar sem PRM_005.
