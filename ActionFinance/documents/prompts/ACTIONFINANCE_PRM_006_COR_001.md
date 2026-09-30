# ACTIONFINANCE_PRM_006_COR_001 — Corrigir autorização e concluir o ensaio de publicação

Data: 29/09/2026. Emissor: analista de negócio, TI e UX. Executor: Cursor.

## Orientação de retomada — atualização após retorno do executor

Este é o mesmo PRM_006_COR_001. Retomar do estado atual, sem reexecutar indiscriminadamente correções já concluídas e comprovadas. Os achados C1–C6 abaixo descrevem a base da revisão original; conferir o código atual antes de alterar. Preservar as evidências existentes e executar novamente somente os testes afetados por mudanças ou ainda pendentes.

Estado informado pelo executor:

- `ops/aws/terraform`: provider AWS 5.100.0 e `terraform validate` bem-sucedidos. Nada aplicado. Preservar essa evidência; sintaxe válida não comprova implantação remota.
- Build Docker interrompido em `mvnw dependency:go-offline` após cerca de 11 minutos, código -1. Não há image ID local. A interrupção, isoladamente, não determina a causa.
- Imagem executada, HTTPS e jornada OIDC no navegador continuam **BLOQUEADOS**.

Prioridade da retomada: concluir C4 e C6 e conferir os resultados das demais correções. Capturar a saída detalhada do build/Maven, sem expor segredos; identificar se existe progresso de download, falha de DNS/TLS/proxy/repositório ou resolução de dependências. Não repetir tentativas silenciosas longas nem classificar tempo decorrido como diagnóstico.

Se `dependency:go-offline` estiver sendo o obstáculo, avaliar removê-lo como etapa preparatória e resolver as dependências no próprio `package`, com cache Maven apropriado. Essa etapa antecipada não é requisito de aceite. Alternativamente, compilar o JAR no host/CI e copiá-lo para a imagem de runtime, desde que o script confira cada exit code, impeça artefatos antigos e registre a correspondência entre fontes, testes, JAR e imagem. Não copiar credenciais Maven/proxy para camadas da imagem. Não desabilitar TLS, pular verificações obrigatórias ou atualizar o stack para contornar o bloqueio.

Depois de obter a imagem, executar o ensaio isolado HTTPS/OIDC e a jornada de navegador prevista abaixo. Registrar image ID, comandos, resultados e evidências. Se persistir impedimento externo, entregar causa delimitada e insumo necessário, mantendo o gate bloqueado e concluindo o trabalho independente. Não declarar sucesso com base apenas em Dockerfile ou Terraform válido.

## Objetivo e limites

Concluir o PRM_006 corrigindo C1–C6 do parecer do analista. Não é PRM_007. O aceite do PRM_006 permanece pendente. Não ativar DNS/produção, aplicar infraestrutura remota, enviar mensagens, criar serviços pagos, fazer commit/push ou alterar outros produtos. Cursor continua responsável pela implementação; este prompt é a orientação do analista.

Trabalhar apenas em `C:\Projetos\ActionFinance`. Ler instruções aplicáveis e preservar os dados/volumes locais. Não alterar regras globais para ocultar divergências; registrar o escopo autorizado. Copiar este prompt integral para `documents/prompts/ACTIONFINANCE_PRM_006_COR_001.md` e o parecer do analista para `documents/reviews`, preservando texto/autoria.

Fontes na pasta do analista: `C:\Users\Oscar Sarquis\Documents\Codex\2026-09-25\files-pasted-by-the-user-documento\outputs`.

Preservar Java 21/Boot 3.4.2, PostgreSQL/Flyway, marca, layout, lógica financeira e autonomia do produto. Não criar integrações. ActionHub mantém o módulo de pagamentos. Sem remodelagem dos ciclos aprovados.

## C1 — Autorização por empresa, inclusive na repetição idempotente

O código atual agrega `FinancePermissions.union(roles)` em `IdentityAuthorizationService`; `CompanyAccessService.requireWritable` não exige papel de escrita na empresa solicitada. A UI também usa permissões globais. Corrigir o conjunto, não apenas ocultar botões.

1. Representar no principal/contexto autorizado a relação empresa → permissões ou papel. Preservar ator estável e escopo tenant/empresa. Permissões globais de navegação não autorizam escrita financeira.
2. Para cada comando de títulos, cadastros, contas, recebimento/pagamento e estorno, verificar no backend a permissão da operação **na empresa do recurso/pedido**, incluindo recursos cujo companyId precisa ser carregado. Não confiar na empresa selecionada pelo navegador.
3. Autorizar antes de consultar/devolver replay idempotente; revogação não pode ser contornada por chave já usada. Manter escopo da chave e resposta original, sem mudar regras de dinheiro.
4. Ler o vínculo atualizado a cada pedido conforme contrato do PRM_006. Bloqueio, revogação e downgrade devem valer no próximo pedido protegido.
5. Expor permissões por empresa na API de acesso e fazer controles da UI dependerem da empresa selecionada. Troca de empresa elimina controles que deixaram de ser permitidos. O servidor continua sendo a autoridade.
6. Preservar a demo local com adaptação explícita ao contrato neutro; não conceder poderes adicionais para evitar quebrar testes.

Prova: mesmo usuário OPERATOR em A e VIEWER em B. Ler ambas; escrever em A; receber 403 ao tentar criar/corrigir/confirmar/cancelar título, alterar cadastro/conta, baixar e estornar em B. Verificar ausência de efeitos e de vazamento de replay. Executar ao menos caso em empresas de tenants distintos. Testar downgrade e revogação na sessão ativa. UI oferece somente ações permitidas na empresa atual.

## C2 — Saída, expiração e operação de resultado desconhecido

`signOut` hoje descarta status HTTP e limpa estado em finally. Corrigir o contrato para só indicar sessão encerrada após confirmação do servidor. Pode usar resposta 204 para logout da SPA ou contrato igualmente verificável. Recusa por CSRF, 5xx e erro de transporte não são sucesso.

Limpar imediatamente a informação financeira visível ao solicitar saída, mas, se a saída não for confirmada, mostrar: **“Não foi possível confirmar a saída. Tente novamente.”** Oferecer repetição de logout. Não reexibir dados automaticamente. Distinguir logout local do logout no provedor, sem prometer encerramento corporativo.

Distinguir escrita nova recusada por 401 de repetição de escrita cujo resultado já era desconhecido. No segundo caso, preservar a incerteza e não liberar silenciosamente uma nova chave. Não tratar o 401 da repetição como prova de rollback da primeira execução.

Manter pendência em memória fora da vida do formulário enquanto a página existir, associada a ator/empresa/chave/rota/corpo. Sem persistir corpo financeiro em storage. Se retornar à sessão sem perder essa memória, oferecer repetição explícita somente após verificar mesmo ator/empresa. Nunca reenviar automaticamente. Ao trocar ator, retirar a pendência de acesso da nova identidade e limpar dados protegidos.

Quando a entrada OIDC provocar navegação completa e perda inevitável da memória, avisar **antes de entrar novamente** que o resultado anterior não foi confirmado e que o usuário deve conferir os registros antes de lançar de novo. Não anunciar “não registrado”. Não inventar recuperação persistente neste corretivo.

Apresentar aviso de sessão expirada no nível da aplicação, mesmo depois que a tela de formulário for desmontada. Não depender de mensagem em componente já removido.

Provas frontend: logout 403/500/transporte e sucesso; escrita efetivada com resposta perdida → repetição 401 → mesma identidade; outra identidade não vê nem repete pendência; navegação de login com aviso de conferência. Preservar os testes anteriores de idempotência.

## C3 — Configuração de produção estrita

Substituir validação por prefixo por parsing de URI. Produção exige HTTPS para origem pública, callback e issuer; host válido, sem userinfo/fragmento. Origem pública é uma origem, sem query/path arbitrários. Callback pertence à origem configurada e tem a rota exata do registro OIDC. Não hardcodar o domínio do primeiro cliente no núcleo autônomo do produto.

Recusar Secure=false em produção e combinações production+demo ou production+perfil de exceção HTTP de teste. Local HTTP pode existir em teste isolado, não como escape dentro do validador de produção. Configuração do cookie precisa corresponder à validação efetiva, sem uma propriedade validar true e outra produzir false.

Delimitar confiança no proxy: serviço acessível apenas pelo ingresso autorizado; documentar tratamento de headers encaminhados e provar que headers fornecidos pelo cliente não alteram callback/origem. Não confiar indiscriminadamente em headers se o processo também for diretamente acessível.

Provas unitárias/configuração: rejeitar HTTP, host `127.0.0.1.evil.example`, URL com userinfo, callback de outra origem, Secure=false e demo habilitada. Ensaio HTTPS mostra AFSESSION Secure/HttpOnly/SameSite=Lax/host-only e CSRF funcionando.

## C4 — Build verificável e ensaio reproduzível

Verificar explicitamente o exit code de cada comando nativo em `build-production-image.ps1`, incluindo npm ci, npm run build e docker build, na versão de PowerShell suportada. Parar com código não zero; nunca imprimir Built após falha. Impedir consumo de dist antigo após build fracassado, com tratamento limitado à pasta de build do próprio projeto. Não apagar caminhos calculados sem verificar seu destino.

Não baixar segurança de TLS nem expor Docker TCP para contornar problemas de rede. Diagnosticar falha de pull e usar ambiente autorizado disponível se necessário. Gerar imagem e executar de fato antes de dar esse gate como aprovado. Registrar image ID local e, somente se existir registry autorizado já usado no ensaio, digest; não inventar digest remoto nem fazer push neste ciclo.

Entregar modo documentado de ensaio com Postgres e IdP descartáveis, HTTPS local confiável pelo navegador de teste, hostname/issuer coerentes para backend e browser, sem reutilizar portas/volumes dos produtos. Não é preciso um IdP corporativo real para esse ensaio.

Fixtures/senhas fixas de teste ficam identificadas como exclusivas do ensaio e fora do pacote de produção. Não usar `bootstrap-prod-like.sql` com senhas change-me como instrução de produção. Manter credenciais fora de logs e imagem.

Provas: falha deliberada de uma etapa encerra script sem mensagem de sucesso; build bem-sucedido produz imagem nova; imagem sobe, serve assets/rotas/API, sem Vite dev, e funciona sem Spider/Hub/Panne. Testar API inexistente sem receber index.html.

## C5 — Completar pacote de infraestrutura, dados iniciais e recuperação

O README AWS atual é uma descrição. Entregar definições parametrizadas concretas de serviço/ingresso e configuração de banco/segredos compatíveis com o alvo recomendado; Terraform/CloudFormation ou formato da infraestrutura identificada. Validar sintaxe localmente. Não aplicar, não importar state de outros produtos e não presumir que parâmetros placeholders representam recursos existentes.

Usar a conta/região levantadas como referência documentada, não repetir pergunta sobre usar infraestrutura existente. Identificar o que será novo ou reutilizado, isolamento, dependências, porta, health, TLS, rede privada e referências de segredos. TLS de ALB e CloudFront têm escopos regionais diferentes: declarar a arquitetura escolhida e os certificados que ela requer, sem concluir ausência global por consulta a uma só região. Não tratar WAF e IdP como alternativas equivalentes. Não adicionar CloudFront/WAF apenas por copiar sandbox se não houver necessidade demonstrada.

Entregar procedimento administrativo transacional e repetível de criação inicial de tenant/empresa em banco vazio, com dry-run e valores explícitos do responsável, antes de `access-admin`. Não criar entidades reais fictícias nem abrir cadastro público. Testar com dados descartáveis. Documentar como obter issuer+subject por procedimento seguro, sem pedir ao usuário para adivinhar identificadores técnicos.

Entregar procedimento executável de migrations separado do runtime operacional e explicar credenciais/grants. Não alterar checksums de migrations já aplicadas. Se necessário mudar grants/modelo, acrescentar migration. Atualizar DAT com estado final e matriz de permissões por empresa.

Ensaiar instalação vazia e upgrade V5 → versão atual em cópias descartáveis, preservando fatos/checksums. Backup/restore deve cobrir as novas tabelas e owner/grants. Definir política explícita para sessões restauradas: preferir invalidá-las após restauração operacional, preservando dados financeiros e auditoria. Testar o procedimento escolhido.

Completar runbook com comandos/parâmetros reais, backup automatizável, referências de armazenamento protegido, retenção proposta, health/alertas configuráveis e rollback sem apagar migrations. Corrigir afirmações antigas apresentadas como atuais, como “ainda não há dados financeiros” e bloqueio de Testcontainers já resolvido. Manter histórico como histórico.

## C6 — Evidências de encerramento

Executar conjunto focado, com zero skip oculto:

- Maven verify, incluindo C1, bloqueio/revogação no HTTP seguinte, CSRF em escrita financeira e logout, recusa de identidade inválida/issuer ou audiência inválidos, mesmo email sem herdar subject.
- Restart da aplicação mantendo banco/sessão e continuidade autenticada, seguido de revogação e logout efetivo. Usar HTTPS no ensaio de cookies do perfil produção.
- Frontend lockfile, lint/test/build/audit; C2 e permissões por empresa na UI.
- Navegador real automatizado com OIDC e imagem ensaiada, em 360/768/1280: entrar → empresa → título → baixa parcial → extrato → sair. Headless é aceitável com capturas e assertions. Java HttpClient comprova protocolo, não substitui navegador.
- Usuário de papéis mistos, troca de empresa e tentativa de escrita recusada. Testar sessão expirada e retorno de entrada sem duplicação de fatos.
- Build, grants, upgrade e restore de C4/C5.

Registrar comandos, saídas, contagens, capturas e caminhos. Não usar capturas PRM_005 como prova da entrada OIDC. Não exigir nova auditoria estética completa; verificar apenas UX e continuidade afetadas pelo ciclo.

Se algum gate permanecer bloqueado por ambiente, reportar **BLOQUEADO**, causa e tentativa concreta; terminar as demais correções sem inventar sucesso. IdP real, DNS e recursos remotos continuam pendências externas de ativação, não impedimentos aos testes descartáveis acima.

## Retorno esperado

Relatório `documents/reviews/ACTIONFINANCE_REV_006_COR_001.md`, com tabela C1–C6 (alteração, prova, resultado), limitações restantes e arquivos entregues. Preservar REV_006 original; vincular parecer/corretivo no índice. Distinguir implementação pronta, comprovada localmente e ainda não validada no alvo remoto.

Ao concluir, parar para revisão focada do analista. Sem PRM_007, publicação, autoaceite, commit ou push.
