# SPIDER — Prova de funcionamento público 001

Data: 02/10/2026. Ordem de estabilização e comprovação do PRM_009, não novo desenvolvimento funcional.

## Resultado da auditoria disponível

O analista releu ACTIONFINANCE_REV_009_INC_002. Há relato de chamada pública READY/9 reviews e de persistência no Finance, run 7a179653-15d5-44f8-9f29-f9fe7486d535, mensagem afm-d3288e80-77cb-41d6-8c6d-8e0214ad25c3. Os testes de retomada do Monitor foram executados em preview local. O próprio relatório deixa a jornada autenticada do Monitor sem prova. A captura posterior do proprietário continua sem transações visíveis.

Portanto: funcionamento integral da Spider na jornada pública NÃO COMPROVADO. Não classificar toda a plataforma como inexistente/falsa nem declarar sucesso com base em evidência parcial.

## Mandato ao Cursor

Concluir diagnóstico, correção e comprovação dentro da autorização de recuperação vigente. Não devolver mais um “publicado, falta você testar” com base em health/HTML/401 ou em teste local. O próximo resultado deve ser evidência verificável de execução pública completa ou uma dependência externa concreta, documentada.

Não iniciar funcionalidades, novos ciclos ou redesign. Não movimentar dinheiro, criar cobrança, aplicar reparo histórico pendente, inserir recebimentos manualmente ou fabricar eventos. Preservar fatos financeiros e controles de segurança.

## Prova A — Uma execução real identificável de ponta a ponta

Primeiro rastrear a execução já informada acima, evitando novos cliques aleatórios. Confrontar: run persistido no AF, mensagem/decisão/provider na Spider, chamada recebida no Hub, resposta da origem e registros persistidos no AF. Identificar cada vínculo com IDs e horários, não apenas totais iguais.

Se a evidência remota dessa execução se perdeu, registrar exatamente o que foi preservado e o que não foi. Corrigir o mecanismo necessário para a prova seguinte antes de gerar outra execução. Não chamar reconstrução parcial de histórico original.

Depois da correção, executar a jornada pública autenticada: Finance Loja de Pães → sincronização → link → Monitor, com captura contínua ou sequência de evidências datadas da mesma sessão/execução. A sessão/credenciais não podem aparecer na gravação ou arquivos publicados.

Comprovar origem ActionHub de produção, itens/reviews reais, correspondência por identidade/valores/status, nenhuma duplicação na repetição e nenhum efeito sobre títulos/baixas/movimentos. Preservar desconhecidos como desconhecidos. Comparar o resultado ao inventário da janela, não a contagem fixa sem contexto.

## Prova B — Monitor público funcional

Abrir o deep link desde sessão ausente quando necessário: login deve preservar destino e selecionar a execução. Lista, detalhe e eventos precisam referir-se à mesma engine e ao escopo autorizado. Zero resultados não pode ser aceito como sucesso dessa prova.

Mostrar as fases e detalhes no formato anterior. Trocar de aba, retornar e comprovar seleção/fases preservadas e atualização coerente. Demonstrar autorização de empresa sem ampliar acesso. Reproduzir e resolver a perda de q/execution no retorno se ela ocorrer; não presumir a causa pela captura.

## Prova C — Execução canônica controlada

### Questionamento obrigatório: por que as simulações não funcionam no público?

O proprietário relata que as simulações estavam habilitadas localmente. Nas capturas públicas, cinco cenários estão desativados e o único habilitado, “Sucesso em múltiplas etapas”, responde “Falha ao iniciar neste ambiente”. Isso precisa de diagnóstico e reparo, não de uma nota genérica de indisponibilidade.

Responder com evidências, para cada um dos seis cenários:

1. Estava implementado e funcional na versão local de referência? Qual teste/versão demonstra isso?
2. O código, registro da capacidade/cenário e dependências foram publicados? O que difere entre local e público?
3. Qual condição exata desabilita o botão ou rejeita o acionamento: descoberta de cenários, configuração, contrato, autorização, rota, rede ou dependência? Apontar a decisão no código e a configuração/resposta observada, sem adivinhar.
4. Se houve restrição intencional de ambiente, onde está definida, qual o motivo e se corresponde ao escopo aprovado? “Indisponível neste ambiente” não é resposta suficiente.
5. Qual correção é necessária para restaurar a capacidade pública autorizada e qual prova demonstra que ela funciona após a correção?

Matriz obrigatória: sucesso em múltiplas etapas; retry com sucesso; negativa de negócio; espera/sinal/retomada; callback/reconciliação; falha técnica. Incluir separadamente os links indisponíveis SegSense e SpiderBank, distinguindo navegação sem URL configurada de produto indisponível. Não assumir autorização para publicar ou alterar esses produtos; identificar dependências externas específicas.

Corrigir regressões e configurações faltantes no escopo já autorizado. Não habilitar botões apenas visualmente, liberar acesso amplo, forçar sucesso ou gerar eventos artificiais. Cada cenário deve executar seu comportamento real na engine com dependências de demonstração explicitamente isoladas: retry deve mostrar tentativas; negativa deve mostrar decisão; espera deve aguardar e retomar por sinal; callback deve registrar recebimento/reconciliação; falha técnica deve terminar no estado de falha esperado. O teste passa quando o comportamento esperado é comprovado, não quando todos terminam em sucesso.

Para callback ou sinal, usar somente origem/destino controlados, sem interferir em transações reais. A simulação deve continuar rotulada como demonstração e jamais substituir a prova A de importação real do ActionHub.

Clicar no botão público “Sucesso em múltiplas etapas”, concluir e visualizar fases/resultados na mesma interface. Isso comprova essa função de demonstração, não pagamento real. Não acionar provider financeiro real para esse cenário.

Entregar a matriz completa dos seis cenários com causa anterior, alteração aplicada, versão, execução pública identificada, fases/resultados esperados versus observados e evidência. Restrição ou dependência ainda não resolvida deve permanecer NÃO VERIFICADO/BLOQUEADO com motivo concreto; não equivale a aceite nem dispensa de funcionalidade. Não declarar a simulação inteiramente validada enquanto houver funções previstas sem prova. Execução nova não substitui a canônica histórica de 28/09; sua perda permanece pendência separada.

## Evidência auditável e devolução

Entregar um único dossiê: versões/digests e configurações relevantes, execução e janela temporal, correlações por fronteira, comparação origem/destino em arquivo restrito, evidência do navegador público, resultado de repetição/isolamento e limitações. Relatórios versionados não incluem credenciais, dados de cartão ou dados pessoais desnecessários.

O analista confere a evidência contra as fontes disponíveis e registra o que observou diretamente. Narrativa do executor e screenshots isolados não bastam para aceitação integral.

Se autenticação humana for a única dependência restante, demonstrar antes a conclusão de todos os checks independentes e preparar uma sessão acompanhada para continuar imediatamente após o login. Solicitar apenas essa intervenção; não pedir ao proprietário para executar manualmente toda a suíte. Não extrair cookies nem contornar OIDC. Se não houver sessão acessível ao executor, declarar essa limitação específica sem afirmar funcionamento.

Salvar este protocolo em documents/prompts e entregar SPIDER_PROVA_FUNCIONAMENTO_PUBLICO_001_RESULTADO.md com PASSOU/FALHOU/NÃO VERIFICADO por critério. Sem autoaceite. A conclusão desejada é a prova efetiva, não apenas um plano de teste ou nova publicação.

## Revisão do primeiro dossiê — 02/10/2026

O analista leu o resultado entregue. Telemetria NoOp e perda de returnTo têm evidências relatadas e correções específicas. A nova sonda não é uma execução iniciada no serviço Finance e não encerra a prova A. Não reconstruir eventos da execução anterior.

Antes de solicitar nova intervenção humana, concluir os checks independentes que o próprio dossiê deixou abertos:

1. O relatório afirma que /v1/canonical pode continuar bloqueado no WAF do ALB apesar do behavior CloudFront. Verificar o percurso efetivo autorizado e corrigir eventual bloqueio sem abrir o ingresso global. Não devolver o botão ao proprietário com essa incerteza conhecida.
2. Allowlist restrita explica cinco cenários desabilitados, mas não comprova funcionamento nem dispensa o requisito. Determinar se a restrição corresponde a decisão aprovada; preparar a habilitação restrita dos cenários controlados previstos e suas dependências, preservando autenticação e isolamento. Registrar cada cenário executado ou bloqueio concreto. Não classificar “restrição documentada” como cenário funcional PASSOU.
3. Hashes iguais em duas respostas do provider comprovam estabilidade das identidades retornadas, não idempotência de persistência no AF. Provar a repetição no fluxo AF e comparar registros/revisões antes/depois. titles=0 sozinho não prova ausência de baixas/movimentos: verificar os três conjuntos e seus efeitos pertinentes na mesma janela.
4. Cookie returnTo contendo parâmetros prova preparação do redirecionamento, não login completo. Classificar callback, seleção da execução e fases no browser como NÃO VERIFICADOS até observação efetiva. Não substituir o link da execução nova do AF pelo da sonda para declarar ponta a ponta: apresentar a sonda separadamente.
5. Normalizar a linha temporal: o dossiê informa replace 13:33–13:40 -03 e sonda posterior 13:48Z, horários incompatíveis se referentes ao mesmo dia. Conferir timestamps brutos e registrar UTC com Z e horário local com offset correto. Não alterar horários para caber na narrativa; esclarecer a ordem efetiva e o vínculo dos 22 eventos à revisão publicada.
6. Registrar a indisponibilidade de sete minutos e ajustar o plano de deploy à topologia real. Não mudar percentuais de rollout cegamente: com store RAM, múltiplas réplicas também podem dividir a evidência. Preservar/exportar evidências antes de substituição necessária e definir estratégia de disponibilidade/retensão sem afirmar que memória sobrevive a replace. Não criar custo novo sem decisão.

Após esses checks, preparar uma única sessão acompanhada. O proprietário faz somente login nas abas efetivamente acessíveis ao executor. O executor prossegue imediatamente com sync no AF, deep link da mesma execução, fases, troca de aba, canônica e evidências; não delegar toda a validação ao proprietário. Se as sessões disponíveis forem de outro navegador, resolver a preparação antes de pedir login. Sem captura/extração de cookies, senha ou MFA.

A aceitação continua NÃO. Novas correções não eliminam pendências de canônica histórica, cenários ou regressão Pay. A recuperação e os testes no escopo já autorizado não exigem nova autorização geral.

## Complemento vinculante — falha dos cliques públicos, 02/10/2026

As novas capturas do proprietário mostram os seis botões habilitados, execuções anteriores na lista e, após acionar “Retry com sucesso”, a mensagem “Falha ao iniciar neste ambiente”. A habilitação não comprova funcionamento. As execuções anteriores não comprovam o clique atual. A captura não demonstra a causa técnica: não atribuir novamente a WAF, login ou configuração sem rastrear esta requisição.

### Diagnóstico e correção exigidos

Reproduzir o clique em “Retry com sucesso” na interface pública autenticada e correlacionar horário, requisição efetivamente enviada, status/corpo da resposta sanitizados e logs nas fronteiras pertinentes (browser, CloudFront/Edge, WAF e engine). Identificar se a execução foi recusada antes de nascer, criada e não apresentada, ou executada com resposta tratada incorretamente pela SPA. Se houver executionId, recuperar seu histórico; se não houver, documentar a fronteira que impediu sua criação. Não registrar segredos ou parâmetros de autenticação nas evidências.

Corrigir a causa comprovada e a apresentação do resultado. “Falha ao iniciar” não deve mascarar uma execução já criada. Uma falha transitória deliberada do cenário Retry deve aparecer nas tentativas dessa execução e terminar conforme o cenário; não se confunde com falha do botão. No cenário Falha técnica, FAILED pode ser o resultado correto, mas o Monitor precisa abrir a execução e mostrar a falha deliberada e suas etapas. HTTP 500 sem rastreabilidade não basta.

### Prova obrigatória pela interface publicada

Executar os seis cenários por seus botões públicos. Provas por chamada direta à engine são auxiliares e não substituem os cliques. Para cada acionamento, registrar versão publicada, horário, cenário, executionId completo, resposta sanitizada, destino aberto no Monitor e etapas observadas.

Preservar o formato de fases expansíveis, detalhes e evidências. Distinguir claramente demonstração mock de percurso FORWARD do ActionFinance; o badge/contexto da execução financeira selecionada não pode induzir que uma simulação consultou o Pay real. Não fabricar eventos nem acionar cobrança ou efeitos financeiros reais para demonstrar cenários.

A prova Finance → Spider → Pay → Finance permanece obrigatória e separada. As novas linhas visíveis são avanço de observabilidade, não aceite automático do conjunto.

### Encerramento

O proprietário já concordou com a sessão acompanhada. Aproveitar a sessão acessível; se login for necessário, solicitar somente essa intervenção no navegador preparado e continuar imediatamente. Não devolver ao proprietário outra rodada de testes manuais. A mensagem posterior sobre falhas não revoga a autorização de correção nem concede aceite.

Atualizar o mesmo dossiê com uma linha por cenário: causa comprovada, correção, execução do clique, resultado esperado/observado e evidência. Marcar FALHOU ou NÃO VERIFICADO quando cabível. Sem PRM_010. Aceite integral continua NÃO até revisão das provas.

## Complemento — seleção do Monitor após Retry, 02/10/2026

O Retry pode aparecer SUCCEEDED (verde) sem o cenário estar aprovado. Se o clique na execução não permanece, não é possível conferir tentativas nem o resultado.

Exigido:

- Identificar o que faz a seleção voltar ao Finance.
- Preservar a escolha durante atualizações e troca de aba.
- Manter linha, detalhe, eventos e origem na mesma execução.
- Comprovar a correção no navegador público, sem desligar a atualização automática.

A causa precisa ser demonstrada no código e na sessão pública. Verde na lista não equivale a aceite do Retry.
