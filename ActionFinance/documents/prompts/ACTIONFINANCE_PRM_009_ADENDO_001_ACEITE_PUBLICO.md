# ACTIONFINANCE_PRM_009_ADENDO_001 — Jornada pública como condição de aceite

Data: 01/10/2026.

## Diretriz do proprietário

O proprietário determinou que seu aceite depende do funcionamento público e autorizou o encaminhamento deste adendo ao Cursor. A prova local permanece evidência técnica intermediária. O PRM_009 não será considerado entregue ao proprietário apenas por funcionar em localhost.

Objetivo observável:

1. Entrar em https://actionfinance.actionhub.com.br e acionar a sincronização.
2. Abrir a execução correspondente em https://monitor.spider.actionhub.com.br.
3. Visualizar os fatos da passagem Finance → Spider → provider ActionHub Pay e o retorno.
4. Conferir os registros importados no Finance, vinculados à mesma execução.

Não basta publicar frontend, copiar eventos locais, apontar um link para localhost ou mostrar uma execução canônica de demonstração.

## 1. Concluir o recorte antes de publicar

Concluir ACTIONFINANCE_PRM_009_COR_001: cursor/ordenação coerentes, prova contra PostgreSQL de ausência de perdas nos limites e restore local com dependências, FKs e permissões completas. Preservar o aceite parcial do percurso local.

Inspecionar o estado atual dos três produtos e dos ambientes públicos. Identificar versões/digests, engine usada pelo monitor público, autenticação, contratos disponíveis, provider e destinos de banco. Fazer levantamento inicialmente somente leitura; não inferir que a engine pública está atualizada porque a local está.

## 2. Preparar uma publicação concreta e revisável

Este adendo autoriza concluir as correções e preparar integralmente a publicação. Antes de executar mudanças públicas, apresentar um pacote concreto: diffs, artefatos/digests candidatos, migrations, configuração, destinos, permissões, ordem de implantação, testes, custo incremental e reversão. Solicitar autorização final para aplicar esse pacote; não pedir novamente autorização para a preparação já solicitada.

A separação existe porque o pedido atual aprova o direcionamento e a preparação, mas ainda não há um pacote definido de mudanças no Finance, Spider, Monitor e Pay para aprovar em produção.

Reutilizar a infraestrutura autorizada sempre que compatível. Não criar ALB dedicado ou novo recurso faturável sem necessidade demonstrada e custo aprovado. Não alterar rotas de outros produtos. Não fazer commit/push nem enviar convites/mensagens por este adendo; se o processo de publicação exigir Git, incluir as ações exatas no pacote de aprovação.

## 3. Ambiente público não significa dados de teste misturados à operação

Propor demonstração acessível pelos hosts públicos, autenticada, com ambiente e empresa de teste explicitamente segregados e código real do Hub. Se a infraestrutura não suportar essa separação, apontar a lacuna e incluir a solução no pacote.

Não habilitar local-demo, tokens demo ou flags permissivas de homologação em perfil de produção. Não remover as recusas de segurança para fazer a demonstração funcionar. Implementar configuração própria e restrita para a integração pública, quando necessária, preservando isolamento de tenant, empresa, origem e ambiente.

Não importar dados reais da Loja de Pães por suposição. O pacote deve indicar expressamente se a demonstração usa dados de teste segregados ou leitura de transações reais e quais vínculos serão autorizados. Para a primeira demonstração, preferir teste segregado sem cobranças ao processador.

Sem payout, criação de cobrança, baixa automática, movimentação de saldo ou escrita nos fatos originais do Pay. Panne continua fora deste recorte.

## 4. Acesso e rastreabilidade públicos

Manter OIDC/sessão/CSRF do Finance. O monitor público deve exigir identidade e autorização compatíveis com os dados exibidos; loopback e ausência de login por empresa, aceitos na prova local, não servem para a jornada pública.

Não usar acesso amplo de administrador para mascarar falta de autorização por empresa. O link “Ver execução na Spider” deve abrir a execução correta após autenticação, sem tokens ou segredos na URL, sem permitir consulta a outras empresas por troca de identificador.

Mostrar ambiente de dados, modo do provider e origem real da execução. Corrigir a ambiguidade de “AMBIENTE MOCK” para execuções FORWARD sem rotular tudo como produção. A Spider só afirma os fatos que observou; persistência no Finance é comprovada no Finance.

Avaliar a retenção em RAM e o número de instâncias da engine pública. A execução não pode desaparecer do monitor por consulta a outra réplica. Propor solução compatível com a topologia e declarar a retenção efetiva, sem prometer histórico permanente. Não introduzir por conveniência um novo projeto de mensageria ou de pagamentos.

## 5. Implantação e validação após autorização do pacote

Depois da aprovação do pacote concreto, executar a implantação coordenada na ordem validada. Migrations incrementais, backup recuperável e compatibilidade entre contratos devem preceder ativação da integração. Reversão não deve apagar dados nem fingir que voltar imagem desfaz migration.

Fazer smoke autenticado dos hosts públicos e uma execução nova iniciada pelo Finance público. Registrar correlação nas fronteiras Finance/Spider/Hub e conferir registros no destino. Não reutilizar a correlação local como prova pública.

Provar isolamento de empresa, ausência de credenciais no navegador/logs e integridade dos fatos financeiros. Testar indisponibilidade de forma isolada ou controlada, sem derrubar a engine compartilhada para demonstrar falha.

Entregar links públicos verificáveis, empresa/ambiente escolhidos, horário e identificador da execução e roteiro curto para o proprietário repetir. Não solicitar senha, MFA ou cookies no chat; eventual login humano deve acontecer diretamente no navegador. Nenhuma autoaprovação pelo executor.

## 6. Critério final e documentos

Salvar este adendo integral em documents/prompts/ACTIONFINANCE_PRM_009_ADENDO_001_ACEITE_PUBLICO.md e atualizar REV_009, plano de publicação e guia do proprietário. Separar estados: correções concluídas; pacote pronto para aprovação; implantação autorizada; implantação executada; jornada pública validada tecnicamente; aceite do proprietário.

PRM_007 permanece identificado separadamente. A invalidação de sessões restauradas continua pendente; não declará-la resolvida por esta demonstração nem recriar RDS sem escopo e aprovação correspondentes. A classificação global de publicação deve explicitar essa pendência.

Não emitir PRM_010. O aceite final depende do proprietário conseguir acompanhar o fluxo nos dois endereços públicos. Até lá, registrar a entrega como intermediária, com a próxima ação concreta e qualquer dependência indispensável.
