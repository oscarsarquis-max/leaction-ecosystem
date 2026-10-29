# PRM_009_ADENDO_003 — Valores de cobrança/Pix no Hub e sincronização no Finance

## Objetivo e continuidade

Concluir as duas frentes solicitadas pelo proprietário: valores efetivos visíveis no ActionHub e registros existentes sincronizados no Finance pela Spider, com percurso no Monitor. Continuar PRM_009; não abrir PRM_010. O executor apresentou causa no código, mas o relato não é aceite nem dispensa verificação.

A correção funcional do checkout avulso e da integração é o escopo deste prompt. Preservar os demais fluxos que compartilham public.orders. Não criar cobrança, efetuar pagamento, reembolso ou payout para testar. Não alterar preços ou preencher histórico com R$ 70,00 por suposição. Esse é o preço comercial atual informado pelo proprietário, não evidência de cada transação passada.

## 1. Confirmar e corrigir a persistência no Hub

Verificar ensurePixCharge, fulfillFromApprovedPayment, fulfillOrderPayment, webhook e GET de consulta, identificando todos os chamadores do fulfillment compartilhado. Confirmar como paidAmountCents é calculado e por que é ignorado. Corrigir a fonte de verdade e seus serializadores; não aplicar replace apenas na tela.

Preservar separadamente:

- Valor cobrado: amount_cents registrado na criação.
- Valor pago informado pelo provedor: paid_amount_cents, somente com evidência explícita, unidade e precisão corretas. Não confundir com líquido após taxas.
- Estado do pedido e estado original do Pix/provedor, datas e referência do pagamento. Definir o mapeamento aprovado/approved/PAID sem inventar literal incompatível com o contrato.
- Evidência de ambiente: live_mode ou equivalente obtido de fonte confiável, com proveniência. Token atualmente configurado não prova retroativamente o ambiente de um pedido antigo. Configuração de processo só pode ser evidência se sua semântica, vigência e vínculo com a criação forem demonstrados.

Atualizar atomicamente os campos necessários para não manter orders.status=PAID e pix.status=pending após confirmação válida. Preservar metadados existentes; impedir perda de atualizações concorrentes no JSON. Usar aritmética decimal/unidades mínimas exatas. Não sobrescrever uma observação mais recente com callback antigo.

Webhook duplicado e consulta GET repetida não podem duplicar fulfillment, contrato, outbox, e-mail ou entrega ao satélite. Manter autenticação/validação dos webhooks. Regressão dos fluxos sessão/plano, PanelDX/cartão e assinatura deve cobrir o que o código compartilhado afetar, sem modificar seus comportamentos por conveniência da Loja.

Em amount_mismatch, persistir a observação do provedor com valor/status/referência e motivo de divergência em estrutura apropriada; não marcar automaticamente como quitado nem liberar fulfillment. Divergência não autoriza descartar o valor efetivamente observado. Documentar a diferença entre pagamento observado e confirmação do pedido.

## 2. Corrigir a apresentação do ActionHub

O admin atualmente soma valor_negociado enquanto checkout amount grava amount_cents. Ajustar o contrato e a tela para mostrar valor cobrado e, quando comprovado, valor pago, com rótulos claros. O GET da Loja deve refletir o estado atualizado, preservando compatibilidade para os consumidores.

Não chamar soma de pedidos de receita liquidada. Valores ausentes devem aparecer como não informados, nunca zero. Não substituir silenciosamente valor cobrado por pago; distinguir quando houver diferença. Validar a correção com exemplos de Pix aprovado, pendente, cancelado, valor divergente e cartão do recorte.

## 3. Histórico: investigar sem repetir efeitos financeiros

Para os nove pedidos existentes, inventariar IDs e evidências em armazenamento restrito. Quando necessário e permitido pelas credenciais existentes, consultar o provedor somente para leitura e confrontar referência, conta destinatária, valor, moeda, status e ambiente. Ausência de referência ou resposta inconclusiva permanece pendência explícita.

Preparar plano de recuperação histórica com dry-run item a item, campos anteriores/propostos, fonte e motivo. Não acionar novamente fulfillment/outbox para atualizar o histórico. Não atualizar linhas históricas cegamente a partir do status PAID ou do preço de R$ 70,00.

Este prompt autoriza diagnóstico e preparação do reparo histórico. Apresentar o dry-run concreto antes da aplicação histórica em produção; não bloquear por isso a correção de novos eventos nem a sincronização dos registros já existentes. O material sensível permanece restrito; relatório versionado sem dados de cliente/credenciais.

## 4. Finance: importar a origem existente sem esperar perfeição do payload

Concluir V13, binding lojadepaes/PRODUCTION e imagens AF/Spider dentro da autorização vigente. Os nove registros existem no Hub de produção e possuem valores de cobrança; falta de live_mode não deve impedir sua sincronização para o Finance.

Distinguir dimensões na base/API/UX:

- Origem do registro: ActionHub de produção, app lojadepaes.
- Estado original do pedido: PAID/PENDING/CANCELLED etc., sem rebaixar todos para pendente.
- Valor cobrado: disponível em amount_cents.
- Valor pago: ausente até existir evidência; mostrar “Valor pago não informado pelo ActionHub”.
- Ambiente do processamento: comprovado real, teste ou não comprovado; este último é pendência de revisão, não ausência de registro.

Itens de origem operacional classificados INDETERMINATE devem ser persistidos e visíveis na área de revisão, não apenas contados em reviewCount e descartados. Não incluí-los em totais de recebimento real confirmado até a evidência necessária. Pedidos PENDING/CANCELLED continuam visíveis com status de origem. Homologação sintética permanece separada.

Quando o Hub disponibilizar os campos corrigidos, sincronização incremental atualiza o mesmo registro por identidade de origem, preservando histórico e retirando apenas as pendências efetivamente resolvidas. Não criar títulos, baixas, saldo ou movimentos automaticamente. Não fazer INSERT administrativo no Finance para simular importação.

## 5. Spider e Monitor: requisitos anteriores mantidos

Toda importação e atualização passa AF → Spider → provider Hub → Spider → AF. Preservar seleção da capacidade, autenticação, binding de empresa e ausência de credenciais Pay no AF. Ajustar contrato versionado quando necessário sem quebrar versões anteriores.

O deep link precisa abrir a execução real e suas fases no Monitor público. Preservar o formato anterior (Transação selecionada, DATA PLANE, etapas expansíveis, estados, resultado e evidências), inclusive o fluxo canônico autorizado. Não preencher etapas fictícias.

A preservação da transação canônica original permanece requisito separado e não dispensado. Não criar outra com mesmo ID ou apresentá-la como original. Relatar recuperação, material parcial ou perda comprovada conforme o adendo 002. Persistência durável e custo novo exigem proposta concreta; não condicionar atividades independentes à decisão de um serviço novo.

## 6. Regressão obrigatória de todo o ActionHub Pay

Determinação adicional do proprietário: o Pay está em produção e as alterações exigem testar o funcionamento completo do módulo. A validação não pode se limitar ao Pix da Loja, ao endpoint de integração ou aos testes novos. Esta seção complementa os gates anteriores, sem autorizar transações financeiras reais para teste.

### 6.1 Inventário e matriz de cobertura

Antes de publicar a correção, inventariar rotas, serviços, consumidores, jobs e integrações efetivamente existentes. Cobrir no mínimo os quatro fluxos relatados e qualquer outro identificado:

| Fluxo | Cobertura mínima |
|---|---|
| Checkout avulso da Loja | Pix e cartão; criação autorizada em ambiente de teste; consulta; aprovação; pendência; cancelamento/rejeição; expiração quando suportada; divergência de valor; repetição e concorrência |
| Checkout de sessão/plano | Valores/preço de origem, sessão, confirmação, vínculo com plano/contrato, entrega ao satélite e idempotência |
| Pagamentos PanelDX | Rotas de pagamento e cartão existentes, confirmação, contrato/fulfillment e compatibilidade dos retornos |
| Assinaturas/preapproval | Criação e transições suportadas, notificações, renovação e cancelamento quando implementados; não confundir assinatura com pedido avulso |
| Webhooks e reconciliação | Assinatura/autenticidade, payload inválido, IDs desconhecidos, consulta ao provedor, duplicidade, atraso, ordem invertida, timeout, retry e concorrência com GET |
| Fulfillment e outbox | Conteúdo e destino corretos por app, entrega única do efeito de negócio, retry sem duplicação, falha/recuperação e ausência de entrega cruzada |
| Admin e consultas da Loja | Valores cobrados/pagos, status, filtros, totais com semântica explícita, permissões e compatibilidade da API consumida pelos produtos |
| Integração Spider/Finance | Produção/teste separados, autorização por app/empresa, contrato, paginação, revisão, rastreabilidade e importação sem escrita nos fatos de origem |

Para cada linha registrar cenário, componente/versão, ambiente, dependências reais ou simuladas, resultado, evidência e eventual efeito externo. Se alguma capacidade não existir, marcar NÃO IMPLEMENTADA com fundamento; não fabricar testes de uma API inexistente. Cenário existente não executado continua NÃO VERIFICADO, nunca “passou” por inferência.

### 6.2 Integridade transversal

Validar que as alterações de fulfillment/JSON não apagam metadados, mudam preços, regressam estado, duplicam contratos/outbox ou alteram respostas esperadas por outros consumidores. Valor ausente não vira zero nem preço presumido; diferenças cobrado/pago não são ocultadas. Testar precisão monetária e moeda suportada, conta/app destinatários e preservação de referências do provedor.

Executar a suíte completa disponível do gateway/Pay e testes de contrato dos consumidores afetados, além dos cenários específicos. Criar regressões significativas onde a cobertura das invariantes financeiras estiver ausente. Dados sintéticos são permitidos em testes isolados identificados; jamais devem aparecer no produto como dados reais ou servir de prova de importação operacional.

### 6.3 Ambientes e efeitos externos

Executar cenários de escrita em ambiente isolado/sandbox com credenciais de teste e destinos de webhook/outbox controlados. Provar que nenhum teste entrega e-mail, pedido, contrato, evento ou cobrança ao consumidor real. Não inserir pedidos artificiais em public.orders de produção nem ligar tokens/modos sandbox globalmente no processo operacional.

Em produção, validar versão/configuração efetiva, login/permissões, consultas autorizadas, compatibilidade de rotas, registros existentes, filas/jobs, logs sanitizados e comportamento observado de transações legítimas, sem criar ou alterar dinheiro para teste. Produção não deve sofrer fault injection destrutiva.

Testar a integração externa efetiva no sandbox do provedor quando houver acesso autorizado. Teste com mock prova apenas comportamento controlado; declarar a limitação se o sandbox não estiver disponível. Não solicitar pagamento, reembolso, cancelamento financeiro ou assinatura real ao proprietário como teste rotineiro. Se uma prova real com efeito financeiro for indispensável, apresentar ação, valor, destinatário e consequência para autorização específica; não executá-la por este prompt.

### 6.4 Gate de publicação e regressão pós-publicação

Entregar a matriz preenchida e resultados da regressão do candidato antes de nova publicação. Falhas críticas de integridade, acesso, confirmação ou entrega bloqueiam a publicação desse candidato. Se reparo já tiver sido publicado, completar a regressão imediatamente e, diante de falha crítica, aplicar a recuperação/reversão segura autorizada; não esperar que o proprietário descubra a regressão.

Antes de aplicar, registrar baseline dos fluxos operacionais, artefatos anteriores, configuração relevante, filas e roteiro de reversão. Depois, executar smoke público e verificar erros/entregas nos fluxos afetados, sem fabricar atividade. Ausência de tráfego não prova sucesso: marcar os cenários operacionais ainda não observados e justificar o plano de verificação. Não prometer cobertura total baseada apenas em health 200 ou em uma sincronização da Loja.

Registrar qualquer risco residual e dependência de teste de forma concreta. O analista revisará o conjunto; o executor não pode atribuir aceite a si mesmo. Não iniciar outro ciclo funcional enquanto houver regressão crítica do Pay.

## 7. Testes e entrega

Provar atualização atômica de valor/status, callback duplicado/fora de ordem, consulta repetida, mismatch com evidência preservada e ausência de efeitos duplicados. Verificar consumidores afetados do Hub. No AF, comprovar importação de reviews com dados, atualização da mesma identidade, paginação e isolamento. Rodar gates dos componentes alterados e registrar artefatos publicados.

Executar sincronização pública autenticada da Loja após publicar dependências. Comparar os nove registros relatados contra o inventário atual da origem, justificando diferenças legítimas; não forçar contagem fixa. Demonstrar valor cobrado e ausência/presença comprovada de valor pago. Provar repetição sem duplicação e abrir a mesma execução no Monitor público. Não solicitar login antes de os pré-requisitos estarem disponíveis.

Salvar este prompt integral em documents/prompts/ACTIONFINANCE_PRM_009_ADENDO_003_VALORES_PIX.md e entregar relatório correspondente com diff por produto, evidências, testes, dry-run histórico e pendências. Atualizar DAT/INT/UX e guia. Não declarar aceite por HTTP 200, contagens ou prints isolados; permitir conferência item a item da origem, transporte e persistência.

Incluir no relatório uma seção própria “Regressão completa do ActionHub Pay”, com a matriz da seção 6, resultado anterior/posterior à publicação e distinção entre teste isolado, sandbox do provedor e observação em produção. Preservar logs por execução sem segredos, dados de cartão ou dados pessoais desnecessários.

Sem novas cobranças, movimentação de dinheiro, escrita em fatos Pay sem evidência, ampliação de apps, recursos faturáveis novos ou mensagens automáticas. PRM_007 separado. Aceite do PRM_009 permanece pendente da jornada real e dos requisitos do Monitor.
