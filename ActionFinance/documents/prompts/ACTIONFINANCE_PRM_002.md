# ACTIONFINANCE_PRM_002 — Fundação técnica local do satélite

Versão 0.2 · Prompt do analista para execução pelo Cursor · 25/09/2026

## 1. Missão e autorização

Implemente exclusivamente a fundação técnica local do ActionFinance em `C:\Projetos\ActionFinance`, no monorepo existente `C:\Projetos`. Você é o único desenvolvedor. Preserve a arquitetura e a UX definidas pelo analista.

**Este documento é preparado para aprovação. Ao recebê-lo do proprietário com instrução para executar, essa instrução autoriza o escopo abaixo, sem nova confirmação para tarefas rotineiras.** Se recebido apenas para leitura, não iniciar a implementação. Não inferir aprovação do proprietário a partir do parecer técnico do analista.

Ao final, o backend Java deve subir com PostgreSQL próprio, aplicar migration mínima, apresentar diagnóstico correto e provar autenticação/autorização demo por testes. Frontend mínimo mostra apenas a situação da fundação. Não é ainda o módulo de contas a pagar nem integração Spider.

## 2. Fontes e acertos preliminares

Leia instruções aplicáveis, ARQ_001, ADRs, DAT_001, INT_001, UX_001 e LAC_001 existentes no produto. Leia o parecer:

`C:\Users\Oscar Sarquis\Documents\Codex\2026-09-25\files-pasted-by-the-user-documento\outputs\ACTIONFINANCE_REV_001_PARECER_ANALISTA.md`

Fonte integral do prompt anterior, para correção de rastreabilidade:

`C:\Users\Oscar Sarquis\Documents\Codex\2026-09-25\files-pasted-by-the-user-documento\outputs\ACTIONFINANCE_PRM_001_CURSOR.md`

R1–R4 foram corrigidos pelo Cursor e verificados pelo analista após o retorno final do PRM_001. A entrega documental do PRM_001 está tecnicamente aprovada, sem ressalvas abertas desse ciclo. Preserve esse fechamento e as sínteses anteriores; não repita a execução do PRM_001. Consulte `documents/reviews/ACTIONFINANCE_REV_001_ENCERRAMENTO.md`. Registre parecer do analista e autorização real recebida em campos distintos. Não atribua ao proprietário aprovação de decisões futuras ou de produção.

Ajuste documental autorizado em `.cursor/rules/ecosystem-focus.mdc`: somente atualizar o foco ActionFinance de PRM_001 documental para PRM_002, mantendo os demais produtos protegidos. Essa é a única exceção de escrita fora de ActionFinance. Leia a regra atual antes de editar; se outra frente estiver ativa, não a sobrescreva: aplique o escopo explícito desta tarefa e registre a coexistência. Não parar processos alheios para impor foco.

Clarifique a frase sobre Panne: Panne é fonte de fatos operacionais; futuramente esses fatos podem originar obrigações no ActionFinance, quando houver contrato. Não proibir essa relação nem presumir API de títulos existente.

## 3. Escopo e exclusões

Criar estrutura independente frontend/backend/database/services/scripts, configurações locais, migration mínima, testes e documentação operacional. Não criar Git aninhado ou módulo Maven da Spider.

Não implementar: payable ou outros cadastros financeiros; ledger; conta bancária; idempotência de pagamentos; inbox/outbox de integração; execução financeira; webhook; clientes diretos de Spider/Panne/Hub; mocks bancários; dashboards; telas de contas a pagar; IA; CAP-021; deploy; commit/push.

Preservar alterações preexistentes. Inspecionar Git antes e depois, distinguindo autoria. Não limpar o monorepo, resetar arquivos ou encerrar serviços de outros produtos.

## 4. Stack, versões e estrutura

- Java **21**, confirmado novamente no POM da Spider; sem Node/Python no backend.
- Spring Boot **3.4.2**, Maven Wrapper, pacote `br.com.actionfinance`.
- HTTP Spring MVC com `spring-boot-starter-web`; não copiar `starter-webmvc` ou `starter-flyway` do Boot 4. Usar dependências Flyway compatíveis com Boot 3 e PostgreSQL, com versões controladas pelo BOM quando aplicável.
- Validation, Security, Actuator, Data JPA e PostgreSQL. `open-in-view=false`; Hibernate `ddl-auto=none`.
- Frontend React/TypeScript/Vite, lockfile versionado. Resolver versões coerentes com a referência local; não copiar tokens, código de domínio ou locks incompatíveis. Registrar versões realmente resolvidas. Não atualizar outros produtos.
- JUnit/Spring Test, ArchUnit e Testcontainers PostgreSQL para verificações relevantes.

Domain não importa Spring/JPA/HTTP nem pacotes de outros produtos. Defina interfaces HTTP, application, domain, infrastructure e configuration conforme ARQ. Crie apenas componentes necessários nesta etapa; não adicionar classes vazias para preencher todos os módulos futuros.

Registre Java, Maven, Node, npm, Spring, Flyway, driver e imagem PostgreSQL efetivos em documento de fundação. Não classifique versão observada como testada sem execução.

## 5. Banco e migration mínima

Banco `actionfinance`, schema `actionfinance`, container/rede/volume locais próprios. Inventariar portas e containers existentes; escolher portas livres configuráveis e documentar. Não tomar porta de outro produto. Bind de serviços de desenvolvimento em loopback.

A imagem `postgres:18.6` observada no SegSense é referência, não exigência de compatibilidade com Boot 3.4.2. Verifique suporte efetivo pelo Flyway/driver escolhido. Se incompatível, escolha uma versão PostgreSQL suportada a partir da documentação oficial e teste a combinação, sem alterar Java/Spring da Spider, desativar Flyway ou mudar para H2. Fixe tag exata e registre motivo/evidência; não usar `latest`.

Separar papéis: bootstrap local limitado à preparação do container próprio; migrator proprietário do schema; runtime sem superuser, CREATEDB/CREATEROLE ou privilégio DDL. Backend usa runtime para operação e credenciais Flyway separadas para migrations no perfil local. Não imprimir senhas nem versionar `.env`. Em produção futura, migration fora do runtime será desenho próprio.

Migrations canônicas em `database/migrations`, copiadas pelo build para `db/migration`. Uma migration inicial mínima estabelece política/permissões/comentário do schema quando necessário, sem tabelas de negócio ou sentinelas fictícias. Flyway mantém seu histórico no schema apropriado. Documentar se criação do schema é responsabilidade do bootstrap ou do Flyway para evitar ciclo de permissão. Revogar CREATE indevido do runtime e verificar privilégios.

Nenhuma tabela company/payable/users é exigida aqui. Contexto demo usa configuração técnica isolada, não é cadastro financeiro em memória. Domínio persistido começa no PRM_003.

Volume sobrevive à parada/reinício. Não executar `down -v`, prune ou restore sobre volume existente. Backup de verificação é restaurado apenas em banco/container descartável criado para esse teste. Provar presença do histórico Flyway e reaplicação sem mudança de checksum; não alegar recuperação de dados financeiros que ainda não existem.

## 6. Segurança local definida para esta etapa

Perfil explícito `local-demo` mais flag `ACTIONFINANCE_DEMO_AUTH_ENABLED=true` habilitam um adapter temporário de autenticação **Bearer opaco demo** exclusivamente para API técnica. Tokens aleatórios de alta entropia são gerados localmente, guardados em arquivo ignorado e lidos por configuração. Não há credencial padrão no código nem token em frontend, URL, log, documentação ou resposta. Não são tokens Spider.

Mapeamento server-side fixo do perfil demo para três principais fictícios: operador da empresa A; consulta da empresa A; consulta da empresa B. IDs de atores e empresas são estáveis, UUIDs fictícios documentados. Permissões atuais: `system:read` e `company-context:read`; nomes de permissões financeiras são futuros e não habilitam endpoints. Não criar papel aprovador de pagamento.

Token identifica principal e seus vínculos autorizados; não aceitar `actorId`, papel ou empresa autorizada a partir de headers customizados/corpo. Requisição pode selecionar companyId, sempre validado contra vínculos do principal.

Implementar pelo Spring Security, sem algoritmo criptográfico próprio. Comparação segura dos tokens e tratamento de erros sem vazamento. API stateless, sem autenticação por cookie, HTTP Basic ou formulário nesta etapa. CSRF só pode ficar desabilitado para esta cadeia stateless Bearer; documentar que adoção futura de sessão por cookie exige revisão. Sem login/cadastro corporativo ou liberação automática se a configuração faltar.

Ausência de perfil/flag deixa autenticação demo desabilitada e endpoints protegidos negados. Flag ativa com tokens ausentes, repetidos ou inválidos deve falhar de forma clara, sem imprimir valores. Profile demo não pode abrir listener público. Configurar CORS somente para origens locais explicitamente permitidas; nunca wildcard de credenciais.

O frontend desta etapa não coleta nem armazena tokens e não oferece login. Esta identidade é instrumento de teste da fundação; o fluxo de autenticação da UX operacional será especificado antes de ações financeiras.

## 7. Contrato HTTP próprio mínimo

Estes endpoints pertencem ao ActionFinance e **não são Satellite Contract**.

| Endpoint | Acesso e resposta |
|---|---|
| `GET /api/v1/system/info` | Público, projeção mínima: nome, versão, `stage=FOUNDATION`, `financialOperationsAvailable=false`, `spiderIntegrationStatus=NOT_IMPLEMENTED`; ambiente demo quando aplicável |
| `GET /api/v1/access/me` | Bearer demo válido; actorId fictício, empresas autorizadas e permissões técnicas; sem token/configuração |
| `GET /api/v1/access/context?companyId=<uuid>` | Autenticado e autorizado; contexto da empresa selecionada; consulta técnica, não criação de cadastro |
| `GET /actuator/health/liveness` | Estado mínimo do processo; sem banco como critério de liveness |
| `GET /actuator/health/readiness` | Banco acessível e migrations válidas, além do estado de aceitação; não depende da Spider |

Informação de produto não afirma readiness. Token ausente/inválido: 401. Empresa sem acesso: 403 com mensagem uniforme. UUID inválido: 400. Rotas não previstas não recebem autorização genérica; authenticated unknown path pode resultar 404 após política de segurança. Não expor env, mappings, beans ou detalhes internos do Actuator.

Retornar erro seguro e estável com `code`, `message` e `correlationId`. Correlação HTTP gerada no servidor ou recebida após validação de tamanho/caracteres; eco em header e logs seguros. Não usar correlationId como autorização ou idempotência.

Readiness com banco parado deve responder não pronto/503 após timeout limitado; liveness permanece viva enquanto o processo funciona. Falha de migration impede inicialização utilizável. Desabilitar detalhes de health e de SQL nos logs públicos.

## 8. Frontend mínimo e UX desta entrega

Uma única página de fundação, sem menu financeiro:

- Marca ActionFinance e indicação “Ambiente local de desenvolvimento”.
- Texto “Fundação técnica. Operações financeiras ainda não disponíveis.”
- Estado de disponibilidade da API, obtido realmente do backend.
- Informação de integração Spider “Ainda não implementada”.
- Botão “Verificar novamente” para atualizar diagnóstico, sem polling agressivo.

Não exibir banco pronto a partir do `system/info`; só apresentar readiness se consultada de verdade. Pode manter apenas disponibilidade da API para reduzir exposição. Estados: consultando, disponível e indisponível, com texto/ícone, nunca apenas cor. Erro não vaza URL interna ou stack.

Fundo claro, painel branco, grafite, ação azul-petróleo, fonte de sistema, foco visível, espaço confortável. Responsivo a 360 px e desktop; botão acessível pelo teclado. Não implementar dashboard, números, lista fictícia, seletor empresarial sem dados ou botões de futura gestão.

Todas as chamadas frontend são para o backend próprio; configurar proxy local sem secrets VITE. Não compartilhar código com o frontend Spider.

## 9. Manifesto e fronteira de satélite

Pode criar manifesto **local preliminar** com applicationId/rótulo ActionFinance, identidade técnica candidata `actionfinance`, papel desejado EXPERIENCE, `executable=false`, `acceptedBySpider=false` e status `DRAFT/NOT_CERTIFIED`. Não atribuir versão Satellite Contract financeira ou alegar registro real.

`services/spider-integration/README.md` descreve o bloqueio e os limites; não criar cliente HTTP que envia payload fictício, provider mock ou adapter permissivo. Nenhuma chamada de health à Spider é necessária.

## 10. Operação local

Scripts PowerShell sob `scripts/dev` para configurar ambiente local, iniciar, consultar estado e parar somente recursos ActionFinance. Validar caminhos resolvidos e ownership dos processos/containers antes de operar. Não encerrar processo alheio por número de porta. Helpers em background sem janela visível.

Configuração de secrets local fora de Git, exemplos só com placeholders. Setup não sobrescreve secrets existentes. Nunca imprimir configuração expandida que contenha tokens/senhas. Scripts devem usar diretórios próprios e serem repetíveis; logs ignorados, sem dados sensíveis. Parada preserva volume.

Documentar comandos e pré-requisitos, endpoints, portas efetivas, diferenças entre execução host e container, procedimentos de backup/restore isolado e limitações de autenticação demo. Não escrever utilitários globais de infra nem tocar configuração de sync do monorepo.

## 11. Testes e provas necessárias

1. Compilação e verificação Maven em Java 21; build/lint/test frontend.
2. ArchUnit: domínio sem framework/persistência/HTTP e sem imports dos produtos vizinhos. Validar classes existentes; não criar domínio financeiro só para dar conteúdo ao teste.
3. Testcontainers PostgreSQL: migrations em banco vazio, nova inicialização sem reaplicação indevida, schema/permissões de runtime e rejeição de DDL/superuser. Usar mesma versão PostgreSQL do ambiente local.
4. Security: 401 sem token/com token inválido; sucesso com principal válido; empresa A não lê contexto B; UUID inválido; dados de ator/empresa enviados pelo cliente não promovem privilégio.
5. Profile: sem local-demo, sem flag e com configuração incompleta, nenhum acesso demo liberado. Teste isolamento de CORS e ocultação de Actuator.
6. Health: banco próprio disponível → readiness positiva; banco de teste indisponível → readiness negativa; liveness separada. Nunca parar banco de outro produto para testar.
7. Frontend: resposta real, falha, reconsulta, teclado e layout estreito; nenhuma credencial embutida no bundle.
8. Reinício do container próprio preserva histórico Flyway; backup/restore em destino descartável validado e documentado.

Sem Docker ou dependência acessível, complete as partes independentes e reporte o teste como BLOQUEADO/NÃO EXECUTADO. Não substituir PostgreSQL por H2, silenciar testes ou declarar gate verde. Não executar operações de rede financeiras nem iniciar produtos vizinhos.

## 12. Documentação e entrega

Preservar histórico de PRM_001 e atualizar estado de README/índice para fundação realmente obtida, sem anunciar funcionalidade financeira. Criar:

- `documents/architecture/ACTIONFINANCE_FND_001.md`: decisões concretas, versões resolvidas, portas e configuração.
- `documents/security/ACTIONFINANCE_SEC_001.md`: identidade demo, autorizações, ambientes e limitações.
- `documents/operations/ACTIONFINANCE_RUN_001.md`: execução, diagnóstico, persistência, backup/restore.
- `documents/prompts/ACTIONFINANCE_PRM_002.md`: **cópia integral deste prompt**, separada da síntese de execução.
- `documents/reviews/ACTIONFINANCE_REV_002.md`: provas, comandos com resultado, testes bloqueados e riscos reais.

Manter status de aprovação do proprietário fiel à instrução recebida. Não promover indiscriminadamente dez ADRs, UX completa ou contratos futuros só porque a fundação foi autorizada. Registrar adoção das decisões concretas deste incremento e suas evidências.

Resposta final do Cursor: acertos R1–R4; arquivos alterados; versões/portas; comandos para subir e abrir; endpoints testados; testes passados/falhos/bloqueados; limites restantes; mudanças fora de ActionFinance limitadas à exceção de foco e justificadas. Não reproduzir secrets.

Pare depois da fundação. Contas a pagar, UX de gestão e integração Spider dependem de prompts posteriores do analista. Sem commit, push ou deploy.
