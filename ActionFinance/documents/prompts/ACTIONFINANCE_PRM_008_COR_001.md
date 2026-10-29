# PRM_008_COR_001 — Confiabilidade da consulta via Spider

Data: 30/09/2026. Parecer focado do analista e prompt ao Cursor. Mesmo PRM_008; sem PRM_009, deploy ou pagamento real.

## Parecer

Correto limitar a primeira fatia à **consulta de recebimento/cobrança de teste**. O ActionHub Pay não oferece payout; a centralização futura de pagamentos de todas as origens é arquitetura alvo, não capacidade existente. Não implementar motor de pagamentos no adaptador.

A escolha de contrato satélite 1.3 não será desfeita apenas porque um levantamento anterior sugeriu `/v1/canonical/executions`. O critério é a arquitetura efetivamente implementada: EXPERIENCE declara intenção, Spider autoriza/seleciona/aciona e PROVIDER atende. A proibição de execução direta pelo EXPERIENCE permanece. Não atribuir viabilidade do Pay real a uma prova com simulador.

Leitura estática realizada pelo analista: REV_008, ExternalLookupService, JdbcExternalOperationRepository, HttpActionHubPayCapabilityAdapter, server.js da borda e spider-pay-lookup.js no Hub. Testes não foram reexecutados pelo analista. **Aceite pendente** das correções abaixo. Sem reabrir produto manual, UX geral, PRM_006 ou ingresso AWS.

## C1 — Separar simulador, encaminhamento e origem do dado

Em `spider/tools/actionhub-pay-edge/server.js`, quando PAY_BASE está definido e lookupPay retorna null (HTTP diferente de 200 ou corpo inválido), o fluxo continua nas fixtures. Isso transforma falha de encaminhamento em resposta simulada. `completed()` e `publicLookup()` no Hub também fixam `sandbox: true`, sem demonstrar que a ordem consultada pertence a sandbox.

Corrigir:

- Modos SIMULATOR e FORWARD explícitos e mutuamente exclusivos. Em FORWARD, qualquer falha permanece falha tipada; **nenhum fallback para fixtures**. Um 404 não deve virar pagamento de demonstração confirmado.
- Origem/sandbox vêm de configuração de ambiente validada e/ou metadado confiável do registro. Não reclassificar ordem real como teste. Se não for possível comprovar ambiente de teste, bloquear a consulta deste recorte.
- O encaminhamento deve suportar HTTPS com validação de certificado, timeout e limite de corpo; `http.request` não atende URLs HTTPS. Sem desligar TLS para fazer a prova passar.
- Endpoint e método exatos, validação do envelope e limite de request. Credencial e empresa/app autorizados continuam obrigatórios.
- A rota nova do Hub deve permanecer desabilitada por padrão e restrita ao ambiente isolado previsto. Não expor consulta a dados reais por simplesmente definir um secret.

Provas: Pay retorna 404/401/500, corpo inválido e timeout → nenhuma fixture; SIMULATOR sempre identificado; FORWARD só informa ACTIONHUB_PAY quando realmente obteve resposta válida. Testar HTTPS e preservação da correlação.

## C2 — Identidade da operação, vínculo ao título e concorrência

Hoje a chave é company+externalReference e o fingerprint não inclui titleId. A operação persistida contém um título; consultar a mesma referência a partir de outro título encontra a operação antiga e pode retornar seu vínculo. O padrão ler-depois-inserir e update sem versão também deixa corrida entre consultas.

Adotar uma semântica explícita, sem duplicar operação externa:

- Manter identidade de consulta por empresa/provider/referência, mas **recusar com conflito** a tentativa de associar essa mesma operação a outro título neste recorte. Uma alteração de vínculo futura exige operação própria, não reassociação implícita. Incluir o vínculo no fingerprint semântico correspondente e corrigir o tratamento de registros de teste anteriores, sem editar migrations aplicadas.
- Verificar autorização e vínculo antes de devolver replay. Testar empresas distintas e dois títulos da mesma empresa.
- Tornar criação concorrente e atualização seguras por unicidade transacional e lock/versão apropriados. Duas consultas idênticas não devem gerar 500 por violação de unique nem sobrescrever observação mais recente com resposta atrasada.
- Distinguir repetição de consulta de replay de comando de escrita: a consulta pode buscar um estado atualizado, mas deve preservar a identidade da operação e auditar cada tentativa. Não chamar isso de resposta idempotente imutável.

Provas PostgreSQL reais: concorrência na primeira criação, consultas com respostas fora de ordem, mesma referência em outro título (409), replay após revogação, corpo divergente na mesma identidade.

## C3 — Validação dos resultados e estados financeiros

O adapter hoje verifica status/providerId, mas não valida toda a identidade da resposta. `amountOf` usa Number.longValue (pode truncar/estourar) ou aceita decimal arbitrário. `apply` força CONFIRMED quando o novo estado é diferente, inclusive após divergência de valor/moeda; já o ramo unavailable rebaixa a confirmação para UNKNOWN. REFUNDED/REVIEW_REQUIRED também não têm tratamento consistente de ponta a ponta.

Corrigir:

- Validar schema e identidade da resposta: request/correlation, referência solicitada, provider/capacidade e contexto empresarial/binding conforme contrato efetivo. Não aceitar resposta de outra consulta apenas porque providerId coincide.
- AmountMinor é inteiro decimal exato dentro do limite do modelo, preferencialmente string na fronteira; rejeitar fração, overflow, negativo indevido, campo ausente obrigatório ou formato inválido. Não truncar silenciosamente.
- Separar **última observação financeira válida** de **resultado da última tentativa de consulta**. Falha de transporte mantém a observação anterior e sinaliza que não foi atualizada; não afirma novo estado financeiro UNKNOWN como se anulasse confirmação.
- Divergência de valor/moeda/referência exige revisão e não pode ser apagada pela regra “confirmado não regride”. Preservar dado anterior e evidência da divergência sem substituir silenciosamente o valor confirmado.
- Estorno/REFUNDED posterior é evolução possível de um recebimento confirmado. Representá-lo ou sinalizar revisão explicitamente, sem prendê-lo eternamente em CONFIRMED. Não gerar baixa/estorno financeiro automático.
- Usar timestamp/versão do provider quando confiável; ausência de ordenação suficiente exige comportamento conservador e documentado. Não inventar observedAt de origem para dar aparência de atualização real.

Provas: confirmado→timeout; confirmado→valor divergente; confirmado→estornado; resposta de referência/empresa errada; número fora do limite e fração; resposta atrasada não apaga a mais recente.

## C4 — Durabilidade sem falsa outbox

Hoje `consult` abre transação, insere operação/mensagem como SENT, faz HTTP e só confirma a transação depois. Queda da JVM após envio pode eliminar o registro local da tentativa. `integration_message` com rótulos OUTBOX/INBOX e ON CONFLICT DO NOTHING não é, por si, uma fila durável ou deduplicação antes do efeito.

Para esta consulta somente leitura, implementar persistência da intenção/tentativa **antes** da chamada remota, sem transação de banco mantida durante HTTP. Persistir depois o resultado validado, com controle concorrente. Reinício deve localizar tentativa inconclusa e permitir reconsulta segura, preservando IDs. Registrar cada tentativa com identidade própria; não suprimir todas as repetições pelo mesmo `out-operationId`.

Escolher mecanismo simples proporcional à consulta: não exigir broker ou worker complexo apenas por existir uma tabela com nome outbox. Se for log de tentativas, documentá-lo como log, sem prometer despacho garantido. Se mantiver outbox funcional, demonstrar recuperação e estados efetivos antes/depois do envio.

A Spider em RAM pode permanecer uma **limitação declarada para esta consulta sem efeito de cobrança**. Isso não recebe aceite de idempotência durável de comandos financeiros. Provar restart AF/Spider preservando a identidade persistida no AF e retorno reconsultado, sem alegar memória durável na Spider. Pagamento/criação de cobrança continuam bloqueados.

## C5 — Provas e correspondência do relatório

Executar gates proporcionais aos projetos alterados, registrar comandos/contagens/zero skip e regressão dos contratos 1.0–1.2. Acrescentar os testes C1–C4 e uma jornada real de navegador isolada em 1280/360 para consulta, falha, revisão e recuperação. Preservar marca e ausência de overflow.

Comprovar caminho AF→Spider→provider com correlação em cada salto e contagem/instrumentação de chamadas; desligar Spider deve impedir chegar ao provider, sem fallback. Não basta constatar que existe somente `spiderBaseUrl` na classe.

Pode exercitar o **código real do Hub/Pay localmente**, com banco e fixture descartáveis de uma cobrança já existente, sem criar cobrança no Mercado Pago e sem credencial/dado produtivo. Se isso for possível, provar a rota real lida no código através da Spider e distinguir: Hub real local com fixture ≠ sandbox vivo do processador. Não alterar o núcleo do Hub para simular payout.

Se o Hub local não puder ser exercitado, registrar o bloqueio e manter a prova classificada como contrato/orquestração com simulador. Não afirmar Pay real integrado. Não criar recurso pago para remover esse bloqueio.

Salvar relatório `documents/reviews/ACTIONFINANCE_REV_008_COR_001.md`, prompt integral em documents/prompts e atualizar DAT/INT/UX somente no escopo afetado. Separar alterações AF, Spider e borda Hub. Não misturar o estado documental anterior ao 1.3 com evidência da versão nova.

## Pendência independente do PRM_007

Registrar separadamente que o restore foi limpo antes de comprovar invalidação das sessões restauradas. Não alegar esse gate concluído. Não recriar RDS por iniciativa deste corretivo de integração. Apresentar a pendência operacional ao analista sem pedir novo login ou interromper esta consulta isolada.

## Encerramento esperado

Voltar com tabela C1–C5, evidências e classificação honesta do alcance. Sem autoaceite, deploy, commit/push, dinheiro real, baixa automática, conector Panne ou PRM_009. A prova buscada continua sendo a viabilidade da Spider; garantias não implementadas devem aparecer como limites, nunca como sucesso inferido de um happy path.
