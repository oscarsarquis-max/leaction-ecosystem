# Regressões e validação

29/10/2026. Cenário executável é o que o sistema atual faz. Cenário modelado não “passou”.

## Prova desta auditoria

Comando, no banco isolado `lojadepaes_test`, sem credencial de produção:

`C:\Projetos\lojadepaes\backend\.venv\Scripts\python.exe -m pytest tests/test_prompt105a_journeys.py tests/test_prompt105a_payments.py tests/test_prompt105a_followup.py -q --tb=line`

Resultado: 36 passaram em 100,19 s. Ambiente local. Não é produção e não é carga.

Saúde pública, sem escrita de negócio: `GET /api/v1/health` e `GET /api/v1/ready` em `https://lojadepaes.com.br` responderam 200 em 29/10/2026. `/ready` só executa `SELECT 1`.

Hub, leitura de hashes e do processo, 29/10/2026: conferido no [README](README.md).

Não executados: suíte `pay-regression.test.js` (a falha antiga da linha 158 continua registrada no relatório 105A e não foi afrouxada); navegação administrativa; SQL de produção da Loja; restauração; carga.

## Regras atuais que a expansão não pode quebrar

| Regra | Onde a prova está | Estado em 29/10 |
|---|---|---|
| Finalização só pelo carrinho | Jornadas C01–C12 no arquivo `test_prompt105a_journeys.py` | 36 testes passaram no conjunto, incluindo essas jornadas |
| Várias linhas e uma cobrança | C01 e `test_cart_multiple_items_one_order_one_total_one_payment` | Incluído no mesmo resultado |
| Aceite antes da cobrança quando há avaliação | `start_checkout` e testes de pagamento | Incluído |
| Pagamento não avança produção nem entrega | Testes de reconciliação e o fluxo em `orders.py` | Incluído no comportamento coberto pelos testes de pagamento |
| Produção sem quitação só com exceção explícita | `orders.py:333` | Código confirmado. Não reexecutado um teste específico só dessa frase nesta sessão; os 36 não substituem um ensaio visual |
| Entrega confirmada sai da fila ativa | Regra de `delivery_confirmed_at` já publicada nos prompts 101. Não fotografada hoje | Indício de código e de documentação anterior |
| Exclusão gerencial reversível | `managerial_exclusion.py` | Código confirmado. Sem nova prova de execução |
| Outbox durável e reconciliação idempotente | Testes do adendo e do Hub no relatório 28/10; follow-up incluído nos 36 | Teste isolado da Loja sim. Hub de produção não recebeu chamada de negócio hoje |
| Enriquecer pagamento antigo sem repetir efeitos | Teste do follow-up, dentro dos 36 | Teste isolado |
| Alerta que encerra após recuperação | Teste do follow-up, dentro dos 36 | Teste isolado. E-mail e push contados em separado nesse teste |

## Cenários A01–A14

| ID | No sistema atual | O que esta auditoria mostra |
|---|---|---|
| A01 Compra de pães, várias linhas, um pagamento | Executável | Coberto pelos 36 testes isolados. Risco na expansão: kit não pode criar segunda cobrança nem segundo pedido para o mesmo envio |
| A02 Kit com um parceiro | Só modelo | Dependências em [fluxos-kit-e-estados.md](fluxos-kit-e-estados.md). Não implementado |
| A03 Kit e pão avulso | Só modelo | Uma cobrança proposta; capacidade somada pelo rendimento; obrigação do parceiro só no componente |
| A04 Última vaga | Parcial para fornada da Loja | `holds_capacity` e limites de massa existem. Não há vaga de parceiro. Disputa não foi ensaiada com dois clientes reais |
| A05 Aceite de um lado só | Só modelo | Proposta: sem cobrança. Não contradizer o autoaceite do pão avulso |
| A06 Webhook repetido, atrasado ou consulta fora | Executável no isolado | Follow-up nos 36. Não repetir operação real |
| A07 Falta componente após pagar | Só modelo | Kit indivisível para; substituição explícita; ver D4 |
| A08 Qualidade | Só modelo | Bloqueio de entrega, lote, custo. `ProductionBatch` não basta |
| A09 Reembolso depois do repasse | Não aplicável hoje | Não há repasse. Quando houver, o split não resolve sozinho. F16 |
| A10 Operador A vê dado de B | Não executável | Fronteira atual: não existe B. Testes negativos listados em [perfis-permissoes-dados.md](perfis-permissoes-dados.md) |
| A11 Dois operadores e worker reinicia | Parcial | Bloqueio de linha no pedido e no pagamento. Sem versão de tela. Worker no processo da API, sem prova de duas réplicas |
| A12 Mudança posterior de preço ou receita | Parcial | Snapshot de nome e preço no item. Sem versão de composição nem de participação |
| A13 Histórico do kit | Parcial para pedido simples | Entrega confirmada e histórico existem para o pedido atual. Tarefas de kit não existem |
| A14 Mais pedidos e integração fora | Não medido | Hipótese de carga na arquitetura. Degradação conhecida: consulta financeira falha, alerta aos 90 s, não marca como não pago e não avança produção |

## Matriz futura, sem implementar para fazer passar

Reservar componente uma vez; aceitar só a organização dona; embalado não entrega; conferência incompleta bloqueia; pagamento repetido não duplica participação; estorno gera movimento inverso; push não sai para outra organização; réplica da API não processa o mesmo registro duas vezes; composição v3 permanece na compra depois da v4.

Esses testes nascem no lote que introduzir a capacidade. Não há como aprová-los hoje.
