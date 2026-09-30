# ACTIONFINANCE_PRM_006 — Acesso de produção e pacote de publicação

Data: 29/09/2026. Emissor: analista de negócio, TI e UX. Executor: Cursor.

## 1. Objetivo e autorização

Implementar acesso autenticado adequado à publicação do produto e preparar uma entrega reproduzível em **https://actionfinance.actionhub.com.br**, aproveitando a infraestrutura existente após levantamento. O proprietário confirmou essa direção. Este ciclo entrega código, migrations, UX de acesso, testes e pacote operacional; não é apenas documentação.

O PRM_005 está encerrado pelo analista no recorte de identidade visual e preservação funcional. Copiar integralmente `ACTIONFINANCE_REV_005_ENCERRAMENTO_ANALISTA.md` da pasta de outputs do analista para `documents/reviews`, caso ainda ausente, e indexar. Não atribuir ao Cursor o aceite.

O alvo é a primeira publicação com acesso restrito a usuários autorizados, usando as funções financeiras já entregues. Não ampliar regras de recebimento/pagamento neste ciclo. Não iniciar PRM_007.

Preparar e verificar a entrega antes da ativação pública. Ao final, apresentar o destino concreto, requisitos externos e procedimento de ativação para revisão. Não aplicar infraestrutura remota, alterar DNS, cadastrar serviços pagos ou publicar durante este prompt. Isso delimita este ciclo de preparação; a intenção do proprietário de publicar já está registrada.

## 2. Fronteiras preservadas

- Trabalhar em `C:\Projetos\ActionFinance`, no monorepo `C:\Projetos`. Sem Git aninhado. Sem commit/push neste ciclo.
- Java 21, Spring Boot 3.4.2, PostgreSQL 17.6 e Flyway 11.10.1 permanecem como baseline. Dependências novas compatíveis com o BOM existente. Qualquer incompatibilidade ou vulnerabilidade relevante deve ser explicitada; não atualizar todo o stack silenciosamente.
- ActionFinance é produto autônomo. A operação manual não depende de Spider, ActionHub ou Panne disponíveis.
- O módulo de pagamentos continua no ActionHub, sem mudança em essência. O ActionFinance registra fatos financeiros locais; não executa Pix, transferência nem pagamento externo.
- Integrações futuras passam pela Spider; não criar conector ou contornar o contrato atual para publicar.
- Panne mantém estoque físico e origem das compras. ActionHub mantém suas vendas, assinaturas e pagamentos. Não alterar esses produtos.
- Preservar paleta, logos, proporções e layout aprovados, incluindo logo móvel de 144 px. Não redesenhar as telas financeiras.
- Não expor demo, levar tokens demo à nuvem ou copiar dados demonstrativos para produção.

## 3. Levantamento inicial com resultado objetivo

Ler AGENTS, documentos e código atuais antes de editar. Consultar configurações de infraestrutura apenas para identificar padrões e recursos; não imprimir segredos, arquivos de estado ou pacotes de credenciais.

O arquivo `spider/infra/aws/README.md` encontrado pelo analista descreve **sandbox/homologação**, não produção. Portanto, não inferir que seus recursos estão aptos ao uso real.

Produzir uma tabela de evidências com: conta/região ou servidor de destino; ambiente; ingresso HTTPS; autoridade DNS; serviço de execução; registry; rede; PostgreSQL e isolamento possível; gestão de segredos; logs; backup; identidade existente; permissões de implantação. Para cada item, distinguir **verificado em ambiente**, **documentado** e **não verificado**. Identificadores não sensíveis podem constar; valores secretos não.

Usar acesso remoto somente de leitura quando já disponível. Ausência de acesso não impede implementar autenticação, banco e empacotamento locais. Registrar precisamente o insumo externo faltante, sem inventar resultados.

Recomendar reutilização dos recursos compatíveis, com isolamento do ActionFinance. Não compartilhar banco/schema/usuário de outro produto nem presumir necessidade de um cluster físico exclusivo. Identificar custo incremental e responsável operacional quando houver informação; não inventar estimativas numéricas.

## 4. Identidade de produto

Adotar OIDC Authorization Code com sessão no backend, usando bibliotecas Spring compatíveis com as versões resolvidas. Aproveitar provedor existente se o levantamento demonstrar que é apropriado e acessível. Se não houver, implementar configuração OIDC independente de fornecedor e testar com provedor descartável; registrar a escolha/provisionamento do provedor real como dependência de ativação. Não criar um serviço próprio de senhas nem exigir autenticação pela Spider.

Extrair o principal da aplicação para um contrato neutro, com UUID de ator estável. O adaptador demo pode continuar implementando esse contrato apenas no perfil local. Serviços financeiros não devem depender semanticamente de `DemoPrincipal`.

Requisitos:

1. Validar emissor, assinatura, audiência e proteções state/nonce do fluxo com a biblioteca. URI de retorno pública explícita. Não construir redirect confiando em Host ou headers encaminhados de origens arbitrárias.
2. Identificar o usuário por **issuer + subject**, nunca por email isolado. Não vincular automaticamente contas pelo email.
3. Autorizações de empresa e permissões vêm do banco do ActionFinance. Claims externos, headers, parâmetros ou dados do navegador não concedem privilégios.
4. Sem cadastro público, criação automática de empresa ou concessão automática de operador no primeiro login.
5. Sessão no servidor; navegador sem access/refresh tokens em localStorage/sessionStorage. Cookie de sessão host-only, HttpOnly, Secure em produção, SameSite=Lax e Path=/; sem Domain compartilhado com `actionhub.com.br`.
6. Sessões persistidas em PostgreSQL via Spring Session JDBC. Prazo inicial de inatividade de 30 minutos, configurável e documentado. Logout invalida sessão no servidor. Definir claramente a diferença entre sair do ActionFinance e sair do provedor.
7. CSRF ativo nas escritas autenticadas por cookie, inclusive logout. Integrar obtenção/renovação do token à SPA. Não transportar a desativação global de CSRF da demo para produção.
8. Bloqueio de usuário e revogação de vínculo produzem efeito na próxima requisição protegida, sem esperar expiração da sessão. Reavaliar autorização local, não confiar só no snapshot do login.
9. APIs sem sessão retornam 401 JSON; usuário autenticado sem permissão recebe 403 uniforme. Navegação explícita de entrada inicia o login, sem redirecionar silenciosamente chamadas JSON para HTML do provedor.
10. Perfil produção não aceita tokens demo. Combinação produção+demo deve falhar no startup. Configuração essencial ausente falha de forma clara, sem expor valores secretos.
11. Proteção de sessão contra fixation, origens permitidas explícitas e endpoints fechados por padrão. Preferir UI/API na mesma origem.

## 5. Estrutura de dados — entregar modelo físico

Inspecionar DAT e migrations existentes. Reutilizar tenant e empresa, sem criar universos paralelos. As entidades abaixo são requisitos lógicos; adaptar nomes ao padrão atual, documentando cada mapeamento.

| Entidade | Campos e restrições mínimas | Finalidade |
|---|---|---|
| Usuário da aplicação | UUID PK; nome de exibição; ACTIVE/BLOCKED; created_at/updated_at timestamptz; versão para mudanças concorrentes | Ator estável do histórico e das autorizações |
| Identidade externa | UUID PK; user_id FK; issuer e subject obrigatórios; UNIQUE(issuer, subject); timestamps | Vincular identidade OIDC ao ator local sem usar email como chave |
| Vínculo de empresa | UUID PK; user_id FK; tenant_id e company_id com FK composta válida; papel VIEWER/OPERATOR; ACTIVE/REVOKED; versão; UNIQUE(user_id, tenant_id, company_id) | Autorizar acesso e papel por empresa |
| Auditoria de acesso administrativo | UUID; instante; ator responsável ou executor administrativo identificado; alvo; ação; motivo; correlação; metadados mínimos sem segredos | Rastrear concessão, revogação, bloqueio e vínculo de identidade |
| Sessões e atributos | Estrutura PostgreSQL oficial da versão resolvida de Spring Session, índices por sessão/expiração/principal | Manter sessão e limpar registros expirados |

Documentar tipos, nullability, PK/FK, índices, unicidades, exclusão/retenção e escopo de cada tabela. Acrescentar diagrama ER relacionando usuário → identidade/vínculo → tenant/empresa e ator → fatos financeiros existentes.

VIEWER e OPERATOR reutilizam a matriz de permissões já aplicada. Enumerar explicitamente ações permitidas por papel. Não introduzir um administrador global de negócio pela conveniência do bootstrap.

Preservar UUIDs de atores e históricos demo existentes. Não reescrever autores de fatos antigos nem atribuí-los a usuários reais. Caso seja necessário criar FK a partir de histórico legado, apresentar e implementar tratamento compatível que preserve a autoria original; não fabricar identidades OIDC para atores demo.

Novas migrations somente após a última versão realmente existente; não editar V1–V5 nem presumir que V6 esteja livre. Atualizar DAT com DDL efetivo, e não só texto conceitual. Dinheiro, movimentos, idempotência e saldos não mudam.

Runtime continua sem DDL. Grants por tabela: DELETE apenas onde operacionalmente necessário para sessões expiradas, sem ampliar DELETE sobre títulos, baixas, movimentos ou auditoria. Migrator separado. Schema de sessões criado via Flyway; desabilitar criação automática em runtime.

Disponibilizar comando administrativo controlado, fora da API pública, para provisionar usuário/identidade/vínculo e revogar/bloquear. Operação transacional, repetível sem duplicação, com dry-run e auditoria. Exigir parâmetros explícitos, não aceitar concessão genérica a todos os usuários. Não executar cadastro real sem os identificadores fornecidos pelo responsável. Não guardar senhas nesse comando.

## 6. UX do acesso e da continuidade

Entrada de produção mantém marca amarela, base azul e ação **Entrar**. Não mostrar campo de token, diagnóstico de fundação ou referências a testes. Texto de acesso restrito discreto. Tela demo permanece identificada e apenas local.

Após login, abrir a jornada existente de Contas a receber. Uma empresa autorizada: selecioná-la. Mais de uma: oferecer seletor com nomes claros; nunca listar empresas não autorizadas. Nenhuma: página “Seu acesso ainda não foi liberado”, com opção de sair/tentar outra conta e sem informações de outros clientes.

Sessão expirada apresenta mensagem clara e ação para entrar novamente. Falha do provedor oferece nova tentativa sem loop de redirecionamento. API 403 por revogação explica indisponibilidade de acesso sem revelar dados protegidos.

Preservar mecanismo de idempotência e resultado desconhecido das escritas. Não repetir automaticamente uma escrita após login. Não descartar chave de operação de resultado desconhecido como se houvesse rollback. Se a pendência ainda existir em memória e o mesmo ator/empresa voltar, permitir repetição explícita da mesma chave/corpo/rota, após validar o contexto. Outro ator/empresa jamais reutiliza ou visualiza a pendência anterior. Após perda de memória da página, orientar conferência do registro antes de novo lançamento; não prometer recuperação que não foi implementada.

Não persistir corpos financeiros no armazenamento do navegador para facilitar retorno de login. Limpar dados visuais/cache na saída e troca de usuário. Explicar o comportamento de rascunhos não salvos antes de redirecionamento, quando possível.

Testar foco, teclado, mensagens acessíveis e ausência de sobreposição em 360, 768 e 1280 px. Preservar menu, drawer, formulário sujo e logo já aprovados. Não incluir módulos vazios.

## 7. Pacote de publicação

Entregar build de produção reproduzível e imagem(s) de runtime sem dependências do Vite dev server. Preferir frontend compilado servido pela mesma origem da API; documentar estratégia de rotas SPA que não transforme erro de API em index.html. Runtime sem root, sem credenciais embutidas, sem `.local`, fixtures, arquivos de chaves ou tokens no contexto/imagem.

Criar configuração de produção e exemplo com nomes de variáveis, sem valores secretos. Incluir banco runtime/migrator, OIDC, URL pública, sessão, proxy confiável e logs. Nunca derivar segredos reais de arquivos de outro produto.

Preparar definição de serviço/ingresso compatível com a infraestrutura levantada, exclusivamente dentro de ActionFinance. Se faltar acesso ao ambiente, entregar artefatos parametrizados e listar o que impede validá-los. Não declarar uma definição genérica como validada na infraestrutura real.

Banco de produção começa vazio e recebe migrations; nenhuma restauração do banco demo. Cadastros reais iniciais ficam em procedimento separado, com valores fornecidos pelo proprietário. Preservar volumes locais.

Runbook deve conter sequência concreta: backup prévio quando aplicável; migrations com migrator; implantação por versão/digest; configuração HTTPS/DNS do subdomínio; teste de entrada; teste financeiro controlado autorizado; logs e health; rollback de aplicação. Não desfazer migrations apagando dados. Definir compatibilidade da versão anterior com migrations novas e como agir se rollback exigir restauração com perda de escritas.

Incluir backup automatizável, retenção proposta, criptografia/acesso e restore ensaiado em banco descartável. Diferenciar proposta de RPO/RTO de compromisso operacional aceito. Health público mínimo, detalhes restritos; logs sem tokens, cookies, segredos nem payload financeiro completo. Preparar verificações de disponibilidade e alertas com destino configurável, sem enviar mensagens neste ciclo.

Não expor PostgreSQL à internet. Não alterar registros raiz, www, api ou demais aplicações do ActionHub. Não assumir que compartilhar subdomínio significa compartilhar cookie, processo, schema ou permissões.

## 8. Verificações obrigatórias

- `mvnw verify`: unitários e ITs executados, zero skip oculto. Preservar isolamento tenant/empresa e jornadas de título/baixa/estorno.
- Autenticação OIDC com provedor de teste descartável e fluxo real de navegador: login autorizado, identidade não provisionada, duas empresas e viewer. Mocks isolados não bastam como prova do fluxo.
- Sessão sobrevive ao restart previsto; logout invalida; bloqueio/revogação passa a impedir acesso na próxima requisição; cookie correto sob HTTPS de teste.
- CSRF: escrita válida funciona; ausência/token inválido é recusado; token reobtido após login/logout conforme necessário. Tokens demo recusados no perfil de produção.
- Tentativas de identidade inválida/issuer incorreto e manipulação de empresa não concedem acesso. Mesmo email com subject diferente não herda vínculo.
- Expiração/retorno de login e pendência de escrita não causam duplicação nem replay em outro contexto; cobrir o caso de resposta financeira perdida antes da expiração.
- Instalação limpa e upgrade sobre cópia descartável da base V1–V5, grants e backup/restore com novas tabelas; sem mudar checksums antigos.
- Frontend: instalação pelo lockfile, lint, testes, build e audit. Registrar falhas reais, sem mascarar incompatibilidades.
- Imagem de produção: build e execução local em ambiente de teste isolado, assets/rotas/API corretos; ausência de demo e segredos no bundle/imagem; sem depender de Spider/Hub/Panne.
- Jornada real de navegador em 360/768/1280: entrada → empresa → título → baixa parcial → extrato → saída; preservar dados locais existentes, usar dados próprios de teste.

Não executar uma jornada financeira fictícia em banco real de produção. O ensaio deste ciclo usa ambiente descartável.

## 9. Documentação e retorno

Salvar este prompt integral como `documents/prompts/ACTIONFINANCE_PRM_006.md` e relatório como `documents/reviews/ACTIONFINANCE_REV_006.md`. Atualizar índice, DAT, UX e arquitetura apenas nos pontos afetados. Registrar decisões deste recorte sem marcar todos os ADRs antigos como aprovados.

No relatório, apresentar:

1. O que foi implementado e como experimentar o acesso sem revelar credenciais.
2. Infraestrutura existente que pode ser reutilizada, evidências e diferenças entre sandbox e produção.
3. Modelo físico, migrations, autorização, sessões e implicações operacionais.
4. Provedor real: identificado/configurado/testado ou pendente, com insumo exato faltante.
5. Gates executados, resultados e caminhos das evidências; separar provedor de teste de identidade real.
6. Pacote produzido, destino proposto e procedimento concreto de ativação/rollback.
7. Lista finita de pendências externas para publicar, responsável sugerido e impacto. Sem repetir perguntas já respondidas: domínio e preferência pela infraestrutura existente estão definidos.

Não declarar “produção pronta” por testes locais. Não atribuir aceite ao executor. Finalizar este ciclo para revisão do analista, sem emitir PRM_007 e sem ativar o endereço público.

## 10. Referências técnicas

Consultar documentação compatível com as versões efetivamente resolvidas; as páginas correntes podem documentar versões mais novas e não autorizam atualizar o baseline:

- Spring Security, OAuth2 Login: https://docs.spring.io/spring-security/reference/servlet/oauth2/login/core.html
- Spring Security, CSRF: https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html
- Spring Session, JDBC: https://docs.spring.io/spring-session/reference/configuration/jdbc.html

Os nomes de tabelas, scripts e APIs devem vir da versão instalada. Não copiar configurações de Spring Security 7/Spring Session 4 para este projeto sem verificar compatibilidade.
