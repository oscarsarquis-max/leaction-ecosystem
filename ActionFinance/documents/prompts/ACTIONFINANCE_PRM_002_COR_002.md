# ACTIONFINANCE_PRM_002_COR_002 — Encerramento das pendências da fundação

Versão 0.1 — 28/09/2026

Execute somente este corretivo no projeto C:\Projetos\ActionFinance. Você é o desenvolvedor; o aceite será feito pelo analista após o retorno. Não iniciar PRM_003. Não reexecutar PRM_001.

## Contexto e limites

A fundação existe, mas mvnw verify continua falhando. O corretivo anterior melhorou o projeto, porém a revisão encontrou pendências adicionais em parada de processos e restauração.

Preservar Java 21, Spring Boot 3.4.2, PostgreSQL 17.6, Flyway 11.10.1, checksum V1 1488219560, banco e volume PG18 preservados, portas locais 8091/5179/5439, identidade demo e bloqueio de operações financeiras. Não modificar migration aplicada para resolver este corretivo.

ActionHub permanece o módulo de pagamento existente, sem mudança de essência. Integração futura: ActionFinance → Spider → ActionHub. Nenhuma integração será implementada aqui. Panne permanece responsável pelo estoque físico.

Sem contas a pagar, ledger, pagamentos, novas funcionalidades de gestão, produção, piloto, DNS, deploy ou mudanças em Spider/Panne/Hub. Sem Git aninhado, commit ou push. Não alterar configurações globais de Docker/Testcontainers nem regras globais do Cursor. Ler as instruções locais aplicáveis e registrar eventual conflito antes de ações incompatíveis.

## 1. Ler o estado antes de editar

Ler os documentos PRM_002, COR_001, seu relatório ACTIONFINANCE_REV_002_COR_001.md e o parecer do analista deste retorno. Inspecionar POM efetivo, árvore de dependências, descoberta do Docker, scripts de start/stop/backup, testes e package-lock. Registrar branch, HEAD e mudanças existentes sem sobrescrevê-las. Aproveitar correções já válidas.

Salvar cópia integral deste prompt em documents/prompts/ACTIONFINANCE_PRM_002_COR_002.md; registrar execução separadamente.

## 2. D1 — Testcontainers e gate Maven real

Primeira tentativa dirigida: atualizar o conjunto Testcontainers de 1.21.3 para **1.21.4**, mantendo seus módulos alinhados e sem atualizar Spring Boot. A release oficial informa correção da linha 1.21.x para mudanças recentes do Docker Engine; é uma hipótese de solução, não diagnóstico concluído.

Verificar versões efetivamente resolvidas de Testcontainers e docker-java, contexto/endpoint Docker e versões da API do cliente/servidor. Não chamar HTTP 400 de engine desligado quando o CLI funciona. Se persistir, registrar endpoint, estratégia efetiva, versão de API negociada e erro sanitizado; não imprimir segredos nem dumps indiscriminados de ambiente.

Preferir descoberta padrão suportada. Reavaliar o adaptador DockerEnvironmentDiscoverer e a estratégia forçada: remover complexidade desnecessária se a atualização resolver. Se ainda forem necessários, justificar e corrigir mensagens que apontem arquivos de configuração não carregados. Não fixar pipe específico de uma máquina no repositório. Qualquer ajuste adicional deve ficar restrito ao processo de testes/projeto e ser baseado em evidência.

Não abrir Docker TCP, trocar banco por H2, desabilitar Ryuk por tentativa, alterar ~/.testcontainers.properties, suprimir falhas, reduzir o conjunto de testes ou aceitar skips como sucesso.

Executar ao final **mvnw.cmd clean verify**, com Surefire e Failsafe ligados ao ciclo normal, testes de integração efetivamente executados e zero falhas, erros ou skips. Não usar skipITs, skipTests ou filtros no gate final. Diagnósticos dirigidos podem precedê-lo, mas não substituí-lo.

## 3. D2 — Encerrar somente processos comprovadamente próprios

Em Stop-ActionFinanceOwnedTree existe uma varredura global de Win32_Process seguida de Stop-Process por correspondência textual. Remover essa alternativa. Nenhum processo pode ser encerrado apenas por conter actionfinance, java, npm ou vite na linha de comando, nem por ocupar uma porta.

Vincular a execução ao caminho absoluto exato do checkout e a um identificador de lançamento. Registrar PID, horário de criação, identidade do executável e os filhos necessários enquanto a relação de parentesco ainda é comprovável. Revalidar identidade imediatamente antes de encerrar. Tratar wrapper que sai antes do servidor: guardar identidade do processo servidor, sem procurar candidatos globalmente para matar depois.

Se a propriedade não puder ser confirmada, recusar a parada daquele processo com mensagem útil. PID reutilizado ou metadado adulterado não autoriza encerramento. Ausência do wrapper não deve descartar silenciosamente o registro de filhos ainda ativos. Preservar idempotência de start/stop.

Provar com testes seguros: start duas vezes; stop duas vezes; wrapper encerrado antes do filho; metadado inválido/PID reutilizado simulado; outro processo com palavras semelhantes na linha de comando que deve sobreviver. Usar processos descartáveis criados pelo próprio teste; nunca usar outro produto real como alvo. Testes de PID reutilizado podem usar abstração/mocks, sem forçar reutilização no sistema operacional.

## 4. D3 — Restauração utilizável pelos papéis corretos

O dump atual remove owner/ACL e é restaurado como postgres. ALTER SCHEMA OWNER não transfere as tabelas. Reaplicar de forma explícita a propriedade e os privilégios exigidos pelos objetos realmente presentes, usando a política canônica de bootstrap/migrations. Não conceder poderes extras ao runtime para fazer o teste passar.

No container descartável, verificar:

- checksum e versão Flyway iguais à origem;
- schema e objetos de migração com proprietário correto, incluindo flyway_schema_history;
- conexão e SELECT da tabela de histórico usando o papel runtime, e não postgres;
- Flyway validate com o papel migrator sobre o banco restaurado e permissões necessárias para futuras migrations;
- runtime sem SUPERUSER/CREATEDB/CREATEROLE, sem propriedade dos objetos e sem CREATE no schema;
- erro SQL deliberado produz falha real; sucesso só é anunciado depois de todas as provas.

Se necessário provar capacidade de DDL do migrator, usar objeto temporário de teste em transação revertida no banco descartável. Não adicionar migration de produção só para essa prova.

Preservar ON_ERROR_STOP, validação de códigos de saída nativos, isolamento por identificador/labels e cleanup exclusivamente dos recursos deste ensaio. Não tocar volumes preservados nem restaurar por cima da base local. Antes de remover diretório recursivamente, validar caminho absoluto dentro da raiz temporária com limite de separador, não só prefixo textual.

## 5. D4 — Dependência frontend corrigida

O advisory GHSA-82fw-gwwq-j7x9 indica correção em **4.1.11** de Vitest/@vitest/mocker. Avaliar atualização controlada para essa versão ou patch corrigido compatível da mesma linha, alinhando os pacotes Vitest usados. Confirmar engines e peer dependencies com o Node/Vite do projeto; não assumir compatibilidade e não usar --force ou --legacy-peer-deps.

Não usar audit fix --force nem migrar automaticamente para Vitest 5. Ajustar somente dependências de ferramentas necessárias, documentando eventual mudança exigida no Vite e seu motivo. Não forçar override incompatível apenas para ocultar o advisory.

Atualizar lockfile, rodar npm ci, lint, testes, checagem TypeScript, build e npm audit. Registrar dependência/caminho/versão de qualquer residual e sua aplicabilidade, sem declarar audit limpo se não estiver. Preservar ausência de credenciais no bundle. Reutilizar evidências visuais anteriores; repetir navegador se mudanças afetarem a aplicação/configuração de desenvolvimento.

## 6. D5 — Evidências e segurança

Complementar a prova de deny-by-default: token válido em rota protegida não permitida, como /api/v1/payables inexistente nesta fundação, deve ser recusado com 403; requisição anônima deve continuar 401. Não criar funcionalidade de contas a pagar para testar isso. Preservar testes positivos de permissões, isolamento entre empresas, rejeição de headers de privilégio e bloqueio demo fora de loopback.

Guardar resultados da mesma execução final com data e identificação. Na revisão anterior, o resumo Failsafe tinha um erro e os quatro XML de classes tinham um erro cada; evitar mistura de execução completa com diagnóstico posterior. Copiar evidências do gate completo antes de rodar outros diagnósticos. Registrar quantidade efetiva de testes por suíte, exit code e skips.

## 7. Entrega e parada

Produzir documents/reviews/ACTIONFINANCE_REV_002_COR_002.md e atualizar o índice documental. Informar por D1–D5: mudança, evidência, resultado e pendência. Incluir arquivos alterados, versões resolvidas, estado dos processos/containers/volumes, resultados Maven/frontend, provas de backup e ownership, achados residuais e limites.

O gate só é verde com execução real completa. Se o problema externo persistir depois do diagnóstico dirigido, entregar bloqueio reproduzível e sanitizado; não inventar aprovação nem contornar o gate. Distinguir execução do Cursor, parecer do analista e autorização do proprietário.

Parar na entrega deste corretivo. Não emitir nem executar PRM_003. O proprietário retornará o relatório ao analista.

## Fontes técnicas do direcionamento

- Testcontainers: https://github.com/testcontainers/testcontainers-java/releases/tag/1.21.4
- Vitest: https://github.com/vitest-dev/vitest/security/advisories/GHSA-82fw-gwwq-j7x9
