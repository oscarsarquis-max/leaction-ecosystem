# ACTIONFINANCE_REV_006 — Parecer do analista

Data: 29/09/2026. Resultado: **aceite pendente; corrigir o mesmo PRM_006**. Não emitir PRM_007 nem ativar produção.

## Base da revisão

Leitura estática do relatório, segurança, resolução de identidade, autorização financeira, migrations V6/V7, cliente de sessão, teste OIDC, Dockerfile, script de build, Compose, configuração de produção, README AWS e runbook. O analista não reexecutou Maven, Docker, AWS ou navegador. Os 40 ITs e 29 testes frontend são resultados informados pelo executor; não equivalem a todos os critérios do prompt comprovados.

O núcleo entregue é aproveitável: identidade por issuer+subject, principal neutro, tabelas de usuário/vínculo/auditoria/sessão, CSRF e refresh de autorização. Não reabrir os ciclos anteriores ou redesenhar a marca.

## Ressalvas para encerramento

### C1 — Alta: permissões de uma empresa permitem escrever em outra

`IdentityAuthorizationService.resolveUser` aplica `FinancePermissions.union(roles)`. Os serviços financeiros verificam esse conjunto global, enquanto `CompanyAccessService.requireWritable` verifica apenas vínculo à empresa e empresa ativa. O usuário OPERATOR em A e VIEWER em B recebe permissões de escrita globais e passa nas verificações para B. A UI também usa `session.permissions` global em `session.ts`.

Corrigir autorização por empresa e operação em backend e UI. Testar o mesmo usuário com papéis diferentes, incluindo alteração/revogação durante sessão e autorização antes de replay idempotente. O teste OIDC atual usa OPERATOR nas duas empresas, portanto não cobre o caso.

### C2 — Alta: encerramento de sessão e resultado desconhecido não estão comprovados

`api.ts:signOut` ignora o status HTTP de `/logout` e limpa a sessão local em `finally`. Um 403/500 pode aparentar saída concluída enquanto o cookie continua autenticado no servidor. Deve limpar a informação protegida, mas informar saída não confirmada e oferecer repetição, sem afirmar sucesso.

`request` limpa a sessão em 401; 401 é classificado como definitivo. Isso não distingue uma escrita nova recusada de uma repetição de operação anteriormente efetivada com resposta perdida. A UI desmonta o formulário quando perde a sessão. Não foi demonstrada a preservação em memória da pendência anterior nem o aviso de conferência após navegação que destrói essa memória, exigidos no PRM_006. Entregar testes e UX explícitos para esse encadeamento.

### C3 — Alta: perfil de produção admite configuração insegura

`ProductionSafetyValidator` aceita HTTP por `startsWith("http://127.0.0.1")`, que não valida host e admite inclusive sufixos malformados/host diferente. Não exige issuer HTTPS nem Secure=true. `application-production.properties` permite desativar Secure por variável. Exceções para ensaio devem ficar em perfil de teste, sem enfraquecer produção. Validar URIs estruturalmente e testar rejeição dos overrides. Delimitar também a confiança nos headers encaminhados pelo ingresso.

### C4 — Média: script pode anunciar imagem construída após falha

`build-production-image.ps1` não verifica `$LASTEXITCODE` depois de npm/docker e termina com `Write-Host "Built ..."`. `$ErrorActionPreference` sozinho não assegura falha de comandos nativos em todas as versões de PowerShell. Dist antigo pode sobreviver ao build frontend malsucedido. Corrigir propagação de exit code e impedir uso de artefato antigo.

O build Docker e a execução da imagem continuam sem prova. Rede é um bloqueio de ambiente possível; não converte esse gate em aprovado.

### C5 — Média: pacote operacional ainda é descritivo

`ops/aws/README.md` enumera recursos, mas não entrega definição parametrizada de serviço/ingresso exigida no prompt. O runbook não fornece bootstrap de tenant/empresa real necessário antes de `access-admin`, que exige empresa existente. Backup/restore após V6/V7 e upgrade a partir de V5 não têm evidência apresentada. O ensaio Compose usa HTTP local diante de cookie Secure e retorno público no exemplo; precisa de instrução executável de HTTPS/IdP de teste, sem exceções no perfil de produção.

Completar artefatos e procedimentos locais verificáveis. A criação remota de recursos e escolha do IdP real continuam pendências externas, separadas das entregas faltantes do executor. Não precisam ser resolvidas para ensaiar com IdP descartável.

### C6 — Média: cobertura insuficiente dos critérios específicos do ciclo

`OidcAuthorizationCodeIT` comprova um fluxo HTTP real por Java HttpClient, não uma jornada de navegador. Contém login, provisionamento de duas empresas operadoras e CSRF/logout; não comprova restart com sessão, bloqueio/revogação na próxima requisição, cookies HTTPS, rejeição de identidade inválida nem jornada financeira OIDC em 360/768/1280. Testes de serviço e as capturas anteriores não substituem essas provas. Completar o conjunto focado, sem exigir uma nova revisão estética geral.

## Encaminhamento

Executar `ACTIONFINANCE_PRM_006_COR_001_CURSOR.md`. Um único corretivo reúne defeitos e entregas faltantes deste ciclo. Retornar evidências e pendências externas reais; não emitir novo ciclo ou declarar produção pronta.

Continuam confirmados domínio `actionfinance.actionhub.com.br` e preferência pela infraestrutura existente após levantamento. A autorização de reutilização não implica usar a sandbox como produção. O módulo de pagamentos do ActionHub permanece inalterado.
