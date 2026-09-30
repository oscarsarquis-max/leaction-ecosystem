# ACTIONFINANCE_PRM_002_COR_001 — Fechamento da fundação local

Versão 0.1 · 25/09/2026 · Próximo e único prompt do ciclo

## Missão

Corrija e complete o aceite do PRM_002 no ActionFinance. O retorno foi revisado pelo analista: **fundação entregue parcialmente; aceite técnico pendente**. Não iniciar PRM_003, domínio financeiro, telas de gestão ou integração Spider.

Projeto: `C:\Projetos\ActionFinance`, monorepo existente. Cursor continua como único desenvolvedor. A execução deste corretivo é autorizada quando o proprietário o encaminhar com instrução de execução. Não alterar produtos vizinhos, Java da Spider, código Panne/Hub, dados externos, domínio/DNS ou produção. Sem commit/push. Preservar arquivos e evidências preexistentes.

Leia PRM_002 v0.2, REV_002, documentos de fundação/segurança/operação e instruções aplicáveis. Este corretivo especifica o fechamento; não substitui a arquitetura de negócio.

## 1. Achados confirmados pelo analista

| ID | Evidência no working tree | Problema de aceite |
|---|---|---|
| C1 | `backend/pom.xml`, `src/test/resources/testcontainers.properties`, `Foundation*IT` | Endereço npipe específico forçado; testes com `disabledWithoutDocker=true`; execução informada terminou com skips |
| C2 | REV_002 e configuração PostgreSQL | Flyway 10.20.1/PG 18.6 gera aviso de versão não testada; aplicação de V1 não prova compatibilidade suportada |
| C3 | `scripts/dev/verify-backup.ps1` | Não exige exit code de comandos nativos nem ON_ERROR_STOP; relatório admite falha de GRANT, mas marca PASSOU; conta de linhas não comprova restauração consistente |
| C4 | `scripts/dev/start-local.ps1`, `stop-local.ps1` | Start recria processos/PIDs sem checar instância; stop aceita nome java/node/npm como prova de ownership e pode agir sobre PID reutilizado; wrapper e filhos não são controlados de forma demonstrada |
| C5 | `configuration/SecurityConfiguration.java` | `anyRequest().authenticated()` concede autorização genérica a futuros handlers; contraria deny-by-default do prompt |
| C6 | `infrastructure/security/DemoAuthStartupValidator.java`, configuração | Validação demo confere tokens, mas não impede override de listener público pelo ambiente/CLI |
| C7 | `frontend/package.json`, retorno | Não existe script de lint; audit informa 3 vulnerabilidades sem classificação fornecida; verificação em navegador real não executada |

Não declarar exploração ocorrida, corrupção de dados ou impacto das vulnerabilidades npm sem evidência. São defeitos e lacunas de validação da fundação local.

## 2. C1 — Testes de integração efetivos

Diagnostique versões da API Docker/engine, contexto ativo, docker-java e Testcontainers. Consulte documentação/release notes oficiais para escolher correção compatível. Não presumir que HTTP 400 significa exclusivamente npipe; registre causa observada.

Remova do POM/test resources a imposição global de pipe específico da máquina. Use descoberta suportada ou configuração local explícita, documentada e não versionada com caminhos pessoais. Não expor daemon TCP sem autenticação, desligar segurança Docker, desabilitar Ryuk indiscriminadamente ou modificar engine/configuração global para contornar o problema.

Se necessário, atualizar Testcontainers e seus módulos de forma consistente por BOM dentro do ActionFinance, mantendo Java 21 e Spring Boot 3.4.2. Confirmar compatibilidade por execução, sem copiar dependências Boot 4 nem usar latest.

O gate de integração deve **falhar** se Docker/testes obrigatórios estiverem indisponíveis. Remover skip automático da suíte de aceite; se houver caminho unit-only, ele deve ser explicitamente nomeado e não representar aprovação. Configurar Failsafe para lifecycle completo `integration-test` e `verify`; `mvnw verify` é o comando de aceite, não apenas `failsafe:integration-test`.

Corrigir eventuais falhas reveladas pelos testes anteriormente pulados. Inspecionar injeção de parâmetros dos métodos de teste, ciclos de vida de conexões e alcance real das asserções. Por exemplo, o teste de persistência atual recebe `DataSource` no método sem anotação explícita: confirmar resolução e corrigir se necessário. Teste que diz verificar reinicialização/checksum precisa efetivamente comparar antes e depois, não apenas exigir checksum não vazio.

Aceite: relatórios Surefire/Failsafe com testes relevantes executados e zero skips obrigatórios, números totais, falhas e erros informados. Se o bloqueio ambiental persistir, registrar causa e tentativa segura; o ciclo continua pendente, sem H2 ou mocks substituindo PostgreSQL.

## 3. C2 — Matriz PostgreSQL/Flyway suportada

Escolher combinação suportada com evidência oficial e teste. Preferir uma atualização compatível de Flyway core e módulo PostgreSQL no ActionFinance que suporte o PG atual, caso exista e seja compatível com Java 21/Boot 3.4.2. Não alterar Spring/Java da Spider.

Se a opção adequada for PostgreSQL 17, definir tag exata suportada e criar **novo container/volume independente**; nunca apontar uma imagem de major anterior para o volume PG18. Preservar o volume atual e registrar procedimento de transição e rollback. Não apagar dados ou volume existente, mesmo que o relatório diga não haver dados financeiros. Antes da troca, confirmar conteúdo e ownership, guardar backup e não reutilizar dump de major superior em inferior sem compatibilidade comprovada. Neste recorte vazio, nova base/bootstrap/migration em destino novo é opção, mantendo a anterior preservada.

Mesma versão PostgreSQL nos testes e ambiente local. Evidências: versões resolvidas, documentação consultada, migrations limpas, revalidação e ausência de warning de versão não suportada/não testada. Não suprimir o log para aparentar compatibilidade.

## 4. C3 — Restauração verificável

Corrigir `verify-backup.ps1` para checar `$LASTEXITCODE` de cada comando nativo; `$ErrorActionPreference` isoladamente não garante falha de programas externos. Usar `psql -v ON_ERROR_STOP=1` ou restore com opção equivalente; qualquer erro de dump, bootstrap, restore ou validação impede mensagem de sucesso.

Criar destino descartável de nome único e rótulo de ownership desta execução, sem `docker rm -f` preventivo por nome fixo. Preferir não publicar porta; se necessária, escolher livre. Esperar readiness com timeout e sondagem, sem sleep fixo como evidência de pronto.

Preparar papéis e pré-requisitos para restaurar owners/ACL corretamente, ou usar estratégia explícita de dump sem owners/ACL mais reaplicação controlada dos privilégios. Em ambos os casos verificar efetivamente: schema, histórico/checksum/sucesso Flyway, owners e restrições do runtime. Não usar runtime privilegiado para fazer o teste passar. Não expor secrets.

Validar checksums/conteúdo esperado, não apenas `count(*) >= 1`. Provar que uma falha deliberada em destino descartável produz exit não zero e nenhuma mensagem BACKUP_VERIFY_OK. Cleanup em finally só de recursos criados pela execução e cujo ownership seja comprovado. Caminhos temporários únicos, resolvidos e limitados ao espaço de trabalho antes de remover arquivos.

Corrigir REV_002: prova anterior foi **parcial com erros de GRANT**, não restauração plena aprovada. Manter histórico do erro e anexar nova evidência. Ainda não afirmar restauração de dados financeiros inexistentes.

## 5. C4 — Scripts seguros e repetíveis

Start deve detectar processo próprio já saudável e não criar nova instância nem sobrescrever seus metadados. Porta ocupada por outro processo deve gerar erro claro, sem kill. Não anunciar disponível antes do health check real. Se o startup parcial falhar, tratar apenas os recursos criados por aquela execução.

Stop precisa comprovar ownership por metadados do lançamento e identidade atual do processo: PID, instante de criação, caminho/comando contendo a aplicação e contexto de execução. Nome java/node/npm não é prova. Considerar wrappers PowerShell/cmd/npm/Maven e processos filhos: encerramento deve atingir apenas a árvore própria validada. Não encerrar processo por número de porta. PID reutilizado ou metadado inconclusivo → recusar parada e informar.

Validar ownership de containers/rede/volume pelos rótulos/projeto Compose antes de operar. Não remover volumes na parada. Portas devem vir de configuração consistente, sem scripts ignorarem overrides permitidos.

Testar start duas vezes, stop duas vezes, PID obsoleto/reutilizado e porta ocupada por processo descartável controlado. Nunca usar processo real de outro produto como alvo de teste. Evidenciar que wrappers/filhos próprios não ficam órfãos depois da parada normal.

## 6. C5/C6 — Fechar autorização e listener demo

Manter endpoints públicos mínimos. Exigir explicitamente permissões técnicas adequadas nos dois endpoints protegidos e escopo de empresa no caso de uso. Substituir autorização genérica por negação para rotas não previstas. Ajustar expectativa de rota desconhecida/Actuator oculto ao resultado seguro: 403 autenticado é aceitável; não conservar permissividade só para produzir 404.

Não liberar `/error` para métodos/conteúdos arbitrários. Se necessário ao tratamento de falhas, limitar o dispatcher de erro e retornar projeção sanitizada. Não comprometer o diagnóstico HTTP seguro.

Quando demo estiver habilitado, validar a configuração **efetiva** do listener após overrides. Recusar `0.0.0.0`, `::` e endereços não loopback. Se management usar listener separado, aplicar mesma restrição. Testar override por configuração equivalente a ambiente/CLI; defaults em properties não bastam.

Preservar perfil+flag explícitos, tokens únicos/fortes sem impressão, Bearer stateless e ausência de cookie/Basic/form login. Adicionar testes sem local-demo, flag false, tokens ausentes/repetidos, empresa não autorizada, sem permissão, headers de escalada e endpoint novo não autorizado. Não introduzir IdP ou login de produto.

## 7. C7 — Frontend, dependências e prova visual

Adicionar ESLint compatível com React/TypeScript, script `lint` e executar lint, testes e build. Fixar dependências/lockfile de forma coerente.

Produzir auditoria npm com dependência afetada, advisory, severidade, direta/transitiva, runtime/dev, cenário aplicável e correção disponível. Consultar advisories oficiais. Corrigir versões vulneráveis por atualização compatível e direcionada. Não usar `audit fix --force`, não esconder alertas e não equiparar depreciação de whatwg-encoding a vulnerabilidade.

Uma vulnerabilidade em ferramenta de desenvolvimento pode importar para o servidor local; analisar alcance e exposição. Qualquer risco sem correção deve ser documentado com justificativa e devolvido para revisão, não autoaceito nem dado como resolvido apenas por ser devDependency.

Executar navegador real em 360 px e desktop, com screenshots e conferência de overflow, foco, Tab/Enter, labels, falha da API e recuperação pela reconsulta. Usar ferramenta de browser disponível ou Playwright local com dependências de teste restritas ao produto. Não inventar evidência caso não seja possível. CSS existente e Vitest não substituem renderização visual.

UI continua única página de fundação, sem módulos financeiros ou tokens frontend. Verificar que valores de secrets reais não aparecem em bundle/logs sem imprimi-los na própria prova.

## 8. Documentação e critério de saída

Salvar cópia integral deste prompt em `documents/prompts/ACTIONFINANCE_PRM_002_COR_001.md` e evidências em `documents/reviews/ACTIONFINANCE_REV_002_COR_001.md`. Atualizar FND/SEC/RUN/README/índice e REV_002 com estado correto, preservando resultados históricos.

Gate de fechamento:

- PostgreSQL/Flyway suportados, mesma combinação em local e testes.
- `mvnw verify` realmente executa ITs; zero skips de aceite.
- Restore falha corretamente em erro e valida papéis/checksum/permissões no sucesso.
- Start/stop repetíveis e ownership comprovado, sem risco de atingir outros projetos.
- Rotas futuras negadas por padrão e configuração demo pública rejeitada.
- Frontend lint/test/build; auditoria npm tratada e resultado visual comprovado.
- Nenhum domínio financeiro, banco externo, integração Spider, commit/push/deploy.

Resposta final: tabela C1–C7 com arquivo corrigido, teste/prova e resultado; versões/portas efetivas; recursos antigos preservados; testes contados e skips; audit; screenshots; pendências e limitações. Não prometer gate verde se qualquer prova obrigatória continuar bloqueada.

Pare e devolva o relatório. **Não iniciar PRM_003. O analista revisará este corretivo antes do próximo prompt.**
