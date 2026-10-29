# ACTIONFINANCE_PRM_007_ADENDO_001 — Gateway existente e revisão do custo

Data: 30/09/2026. Direcionamento do analista após questionamento do proprietário sobre o gateway existente.

**Natureza: adendo ao PRM_007 em execução.** Incorporar esta orientação ao mesmo ciclo e ao seu relatório. Não substituir o prompt integral, não reiniciar o trabalho e não emitir PRM_008. Este adendo prevalece sobre a previsão de criar ALB dedicado até que a comparação abaixo seja concluída. A autorização de continuidade permanece válida para as demais atividades independentes.

O plano DEP_001 propôs ALB dedicado sem documentar comparação suficiente com o gateway compartilhado indicado pelo proprietário. Isolamento do ActionFinance não exige, por si só, um ALB exclusivo. Reavaliar essa escolha dentro do PRM_007, sem reabrir PRM_006 nem iniciar integração financeira.

Na estimativa apresentada, ALB base (US$ 16,43), consumo de cerca de 1 LCU (US$ 5,84) e dois IPv4 (US$ 7,30) somam **US$ 29,57/mês**. São valores do plano anterior, não nova cotação ou economia garantida.

## Trabalho solicitado ao Cursor

1. Conferir estado real da implantação antes de agir. Se o ALB ainda não existe, não criar o componente dedicado até concluir esta comparação. Se já existe, informar custo/uso atual; não excluir nem interromper serviço em funcionamento automaticamente. Continuar tarefas independentes que não dependam da decisão de ingresso.
2. Identificar por leitura o gateway de produção mencionado pelo proprietário: tecnologia, recurso, região, rotas/domínios atuais, backend e responsável. Não confundir NAT de saída ou S3 gateway endpoint com ingresso HTTP. Não inferir que o API Gateway de callbacks da Spider seja esse gateway compartilhado.
3. Avaliar adicionar `actionfinance.actionhub.com.br` à entrada existente, preservando processos, banco, cookies e permissões próprios. Demonstrar isolamento de rotas e ausência de alteração nas rotas já operacionais.
4. Se for Amazon API Gateway HTTP API, avaliar integração privada via VPC Link e Cloud Map/ECS, além de opções já existentes. Não prometer retirar ALB simplesmente colocando API Gateway à frente de um ALB novo. Se for proxy reverso ou ALB compartilhado, avaliar a configuração equivalente de host/target dedicado.
5. Verificar suporte à aplicação completa: assets da SPA, rotas e API, redirects OIDC, cookies/Set-Cookie, CSRF, limites de tamanho/timeout, TLS, descoberta de tarefas privadas e health. Nenhum bypass de autenticação ou exposição pública direta da tarefa para baratear.
6. Comparar custo incremental total, operação e disponibilidade das alternativas, incluindo componentes adicionais, requisições/dados, certificados, logs e impacto de compartilhar a entrada. Reutilizar infraestrutura existente quando adequado; justificar tecnicamente eventual necessidade de ALB dedicado.
7. Atualizar DEP_001 e apresentar recomendação com evidências e custo. O consentimento anterior de US$ 65–80 não é obrigação de consumir esse valor nem justificativa para manter recurso desnecessário. Não alterar gateway compartilhado antes de preparar plano de mudança e reversão limitado ao novo host; se a mudança exigir afetar outros produtos, explicitar a diferença para decisão.

O analista não identificou o gateway compartilhado nas fontes acessíveis nesta consulta. `C:\Projetos\PanelDX` retornou acesso negado; não contornar restrições. O executor deve usar os acessos já autorizados de leitura ou informar o insumo específico que falta.

Referência técnica: [integrações privadas de HTTP APIs AWS](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-private.html). A documentação permite alvos ALB/NLB ou Cloud Map; a aplicabilidade depende do tipo de gateway realmente existente.

Salvar este adendo integral como `documents/prompts/ACTIONFINANCE_PRM_007_ADENDO_001_GATEWAY.md`, referenciá-lo no PRM_007 e indexar. Registrar a avaliação e a decisão em um adendo do REV_007 e atualizar DEP_001, preservando o histórico da proposta anterior. Permanecem válidos os dados: login `admin@actionhub.com.br` (sem caixa), comunicação `oscar@oscarsarquis.com.br`, empresa Loja de Pães sem CNPJ. Não criar novo ciclo nem tocar no módulo de pagamentos do Hub.
