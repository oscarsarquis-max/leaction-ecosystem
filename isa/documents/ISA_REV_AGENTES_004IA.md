# ISA 0.6.0 — agentes reais e histórico persistente

17/10/2026. Código da imagem: `758bb1c4`. Baseline 1.3. Publicação em `https://isa.actionhub.com.br`.

## Entrega

A categorização acontece depois de salvar o lançamento e respeita a correção da pessoa. A descrição ambígua permanece para conferência. Início e Planejar oferecem **Pedir ajuda à ISA**, pergunta livre, avaliação de gasto, explicação, alternativa e histórico. Guardar um plano preserva o vencimento original e não realiza pagamento.

O modelo é Claude Sonnet 4.5 no Amazon Bedrock: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`, região de entrada `us-east-1`. A versão Sonnet 4 encontrada no PanelDX e no Chamelleon recusou execução por fim de vida; a sucessora respondeu. Nenhuma chave foi copiada desses produtos. O papel `isa-task` recebeu somente a permissão de inferência para o perfil e os modelos correspondentes.

Os limites do piloto são 30 chamadas por pessoa e 100 no serviço por dia, contexto limitado e até 2.000 tokens de saída por chamada. O motor calcula os valores; Claude explica e escolhe entre alternativas calculadas. A análise usa disponibilidade, reservas e compromissos informados; não equivale a um inventário automaticamente completo de todas as obrigações do usuário.

## Persistência

O schema passou a 4, com fila durável `ai_job` e coordenação de quota. Pedido, premissas, resultado, modelo, versão de prompt, uso de tokens e identificador da execução ficam registrados. Sugestões e decisões permanecem em suas tabelas, com isolamento por proprietário. Correções humanas e sugestões desatualizadas são protegidas de aplicação tardia.

A cópia anterior à publicação terminou com código 0. A tarefa diária foi atualizada para `isa-backup:5`. A primeira execução dessa revisão terminou com código 0; o arquivo privado foi lido para verificar o hash e a inclusão de `ai_job`, `suggestion` e `suggestion_event`, sem imprimir seu conteúdo. Manifesto: `2026-10-17T11:59:43+00:00`, retenção de sete dias. A cópia inclui a estrutura e os registros existentes; não foi criada sugestão fictícia na base produtiva.

## Provas

- 26 testes de motor, HTTP, identidade, persistência e IA passaram; os dois arquivos de testes JavaScript de cálculo e extrato passaram.
- No PostgreSQL isolado, os agentes chamaram Claude de verdade com dados sintéticos. A categoria Alimentação foi gravada sem mudar o valor. A análise preservou o mínimo de menos R$ 100,00 calculado pelo motor. A alternativa e a escolha ficaram salvas, sem alterar o compromisso.
- O navegador percorreu a análise e a escolha do plano. As capturas estão em `documents/prototipo/ia-004/analise-desktop.jpg` e `analise-390.jpg`. Em 390 px por emulação, não houve rolagem horizontal; não é prova em aparelho físico.
- Uma tarefa isolada usando a imagem, rede e papel de produção chamou Claude com a frase sintética de conectividade. Terminou com código 0. Request ID: `c8cf1045-1045-491f-9d60-6ff0d7fc7ece`, 25 tokens de entrada e 7 de saída. Não acessou os registros financeiros.
- O host público respondeu saúde 200, versão `isa-piloto 0.6.0`, `ai=claude-bedrock`, readiness 200 com schema 4. `/assistant.js` respondeu 200 e `/api/ai/status` sem sessão respondeu 401.

A sessão autenticada de produção não foi usada nesta rodada. As provas funcionais foram com identidade sintética no laboratório. Não houve importação real, alteração de vencimento nem pagamento produtivo.

## Publicação e recuperação

Serviço ISA: `isa-web:8`. Imagem publicada pelo digest do índice `sha256:7daad36e0b8a6921b1cdaa5d16e1be399f0b511ea8d79687c3696f1bd7620c01`; manifesto linux/amd64 `sha256:ae5a1a1af7d4ce3ef53ddf2eb2fa240eece521f7c69faa1f92d7fcd28c99566a`.

A entrada continua pelo `paneldx-alb` compartilhado. Não houve balanceador, regra de listener ou infraestrutura do Finance nova. O Finance permanece em `actionfinance-web:27`.

Retorno da aplicação: `isa-web:7`. A migração 4 é aditiva; não remover tabelas nem apagar sugestões ao retornar. Manter a cópia diária na revisão 5 para preservar as tabelas novas mesmo durante eventual retorno. A aplicação anterior continuou saudável enquanto a nova já havia aplicado o schema 4.

Cartões continuam reservados ao 005. Leitura de foto e conexão bancária automática não fazem parte desta publicação.

## Repositório

O código está commitado localmente. A tentativa de push ao remoto já configurado `https://github.com/oscarsarquis-max/leaction-ecosystem.git` foi bloqueada pela revisão automática, que exigiu confirmação da propriedade/destino. O vínculo da branch com esse remoto foi confirmado localmente, mas a CLI do GitHub não tinha sessão para verificar a propriedade. A confirmação foi solicitada ao usuário. Isso não bloqueou a publicação na AWS.

Conferência final: rollout COMPLETED, uma tarefa RUNNING e HEALTHY, zero pendentes e zero falhas. Tarefa ativa: 893de1be321d4cdd9419c434ec7f1d98, isa-web:8.

17/10/2026: o proprietário confirmou que oscarsarquis-max/leaction-ecosystem é seu repositório e autorizou o envio dos commits da ISA. A confirmação resolve a pendência de autorização do destino descrita acima.
