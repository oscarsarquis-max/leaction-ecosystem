# ACTIONFINANCE_PRM_007 — Publicação restrita em produção

Data: 30/09/2026. Analista de negócio, TI e UX: Codex. Executor: Cursor.

## 1. Objetivo

Publicar o ActionFinance em **https://actionfinance.actionhub.com.br**, com autenticação real e acesso apenas às pessoas e empresas autorizadas. O proprietário já pediu a publicação e confirmou o aproveitamento da infraestrutura existente após levantamento. Não perguntar novamente pelo domínio ou por essa preferência.

O PRM_006 está integralmente aprovado no escopo de preparação local. Copiar o parecer `ACTIONFINANCE_REV_006_ENCERRAMENTO_ANALISTA.md` da pasta de outputs do analista para `documents/reviews` e indexar. Não reabrir seus corretivos.

Este prompt permite implementação dos ajustes de implantação, levantamento remoto de leitura e preparação de plano executável. A ativação é parte deste mesmo ciclo, condicionada à configuração concreta de recursos/custos e aos dados reais de acesso. Antes de contratar novos recursos pagos ou aplicar o plano remoto, apresentar o plano final e obter concordância do proprietário sobre recursos e custo. Não pedir aprovação abstrata antes de preparar o plano. Uma vez aprovado, prosseguir dentro desse plano sem sucessivas confirmações rotineiras. Se precisar aguardar resposta, concluir o trabalho independente.

Não encerrar como “publicado” com base em Terraform validate, health ou página de entrada. O resultado final exige login real autorizado, isolamento e condições operacionais comprovadas no destino.

## Prioridade de negócio confirmada pelo proprietário — 30/09/2026

A primeira integração funcional após a preparação/publicação é com **ActionHub Pay**, para permitir ao ActionFinance gerenciar pagamentos e recebimentos da **Loja de Pães** existentes no ActionHub. O escopo de negócio não se limita a assinaturas: inclui os fluxos da loja. O módulo de pagamentos continua no ActionHub, sem mudança em essência; o ActionFinance centraliza a gestão financeira.

**Decisão complementar do proprietário:** centralizar no **ActionHub Pay a execução de todos os pagamentos, independentemente da origem**. Obrigações vindas do Panne, do ActionHub, de outros sistemas ou cadastradas manualmente são geridas no ActionFinance. Quando houver integração implementada e autorização operacional aplicável, as solicitações seguem **ActionFinance → Spider → ActionHub Pay**; confirmações, falhas e estornos retornam pela Spider para atualizar o controle financeiro. A centralização não autoriza pagar automaticamente ao importar uma obrigação, nem significa que os contratos necessários já existem. Definir aprovações, idempotência e tratamento de resultado desconhecido no prompt de integração. Uma solicitação enviada não equivale a pagamento confirmado. Manter o registro manual de pagamento externo já realizado, com identificação de origem, para a operação autônoma do produto; esse registro não é um segundo executor de pagamentos.

Também devem entrar nessa gestão as obrigações e os pagamentos relacionados às compras registradas no **Panne (`panne.com.br`)**. O Panne é responsável pelo **estoque físico da Loja de Pães** e origem de suas compras. O destino definido para execução dos pagamentos é ActionHub Pay; levantar os fluxos atuais apenas para planejar a integração e a transição, sem atribuir ao Panne a execução financeira no desenho alvo.

A prioridade orienta o próximo recorte de integração, sem acrescentar conectores ao PRM_007 nem emitir antecipadamente PRM_008. Usar Spider como caminho de integração conforme arquitetura; confirmar contratos reais antes de implementar. Não criar ligação direta para contornar lacunas da Spider.

No próximo levantamento, rastrear compra/venda → obrigação/título → execução → confirmação/estorno, com IDs de origem, empresa, parcelas e valores. Definir a autoridade de cada fato e evitar duplicação entre registros manuais, importações e eventos. Distinguir a execução no ActionHub Pay da baixa gerencial no ActionFinance. Preservar operação autônoma e capacidade de integrar outros sistemas.

Copiar esta orientação para a documentação de domínio/integração durante o PRM_007, como prioridade confirmada pelo proprietário, sem tratar isso como contrato externo já implementado.

## 2. Baseline e fronteiras

- Monorepo `C:\Projetos`, projeto `C:\Projetos\ActionFinance`. Sem Git aninhado. Alterações locais somente em ActionFinance; não alterar código, banco, serviço ou segredos de Spider, ActionHub, Panne e outros produtos.
- Manter Java 21/Boot 3.4.2 e arquitetura aprovada. Não copiar POM de outro satélite. Verificar compatibilidade dos serviços gerenciados com PostgreSQL/Flyway atuais; não escolher versão indisponível por suposição.
- Última imagem local aprovada: `sha256:486e2bef08349c261581664f0136f335801f9b488e2e3997db5faa7a7e229d94`; JAR `b8b8a2f45c6c8df06137a8fc243026f9f77ebc1e20971e975e56971f60d0bd2c`. É image ID local, não digest de registry.
- Se houver alteração de código/empacotamento, gerar nova imagem e registrar correspondência com testes e fontes. Não atribuir à imagem antiga alterações posteriores.
- Publicar apenas as funções já entregues. Registro de recebimento/pagamento não executa dinheiro. O módulo de pagamentos do ActionHub permanece inalterado. Sem integrações novas.
- Preservar marca, logos, paleta e UX aprovadas. Sem módulos vazios, dashboard novo ou administração visual de usuários neste ciclo.
- Não levar dados, tokens, subjects, certificados ou senhas do ensaio para produção. Banco novo de produto, sem restaurar a demo.
- Sem commit/push Git neste prompt. Push de **imagem para ECR** integra a implantação aprovada e não se confunde com push Git. Guardar manifesto de release e hashes para rastreabilidade.

## 3. Levantamento e plano concreto

Revalidar conta, região e recursos por consultas de leitura. Referência observada anteriormente: conta `253137917703`, região `us-east-2`; a Spider usa sandbox. Não tratar sandbox como produção. Não imprimir credenciais, state ou conteúdo integral de secrets.

Identificar VPC/subnets/rotas, saída para ECR/Secrets/OIDC, recursos realmente reutilizáveis, zona DNS, certificado regional, Postgres adequado e provedor de identidade disponível. Preservar a decisão anterior de não utilizar `actionhub-prod`.

Entregar `ACTIONFINANCE_DEP_001.md` com:

1. Recursos reutilizados e novos, nomes/IDs não sensíveis, conta/região e justificativa.
2. Arquitetura proposta: ALB HTTPS → serviço ECS/Fargate privado → PostgreSQL privado; ajustar ao levantamento sem multiplicar componentes sem necessidade. CloudFront não é requisito.
3. Dimensionamento inicial, limitações de disponibilidade e capacidade, backup/retention, logs/alertas e responsável operacional proposto.
4. Estimativa mensal datada com fontes oficiais e premissas: compute, ALB, banco, armazenamento/backup, NAT/endpoints, logs, secrets e identidade. Não esconder custo de rede nem declarar gratuidade presumida.
5. Plano Terraform verificável com resumo de create/change/destroy. Nenhuma exclusão/substituição de recursos de outro produto. Se surgir alteração fora do ActionFinance, resolver o desenho antes de aplicar.
6. Sequência de implantação e reversão, critérios para abrir o endereço ao usuário e insumos reais ainda faltantes.

Apresentar uma recomendação principal ao proprietário para aprovação do gasto/configuração. Não transferir escolhas rotineiras de implementação para ele.

## 4. Login e primeiro acesso real

Primeiro investigar se já há provedor corporativo utilizável. Não presumir que o login do ActionHub seja OIDC compatível. Usar cliente dedicado do ActionFinance, sem alterar contratos ou login de outros produtos.

Se não existir provedor apropriado, a recomendação do analista é **Amazon Cognito User Pool dedicado**, com cliente confidencial Authorization Code e login gerenciado. Incluir opção no plano/custo antes de provisionar. A aplicação permanece OIDC independente de fornecedor. Confirmar interoperabilidade do método de autenticação do cliente com o Spring configurado; não trocar para fluxo implícito nem colocar segredo no frontend.

Configuração: cadastro público desabilitado, callback exato `https://actionfinance.actionhub.com.br/login/oauth2/code/actionfinance`, emissor real HTTPS, escopos mínimos, política de recuperação e MFA definida para usuários reais. Não marcar MFA como comprovado apenas por habilitar uma opção.

Insumos do proprietário: email do primeiro responsável operacional, nome da empresa e CNPJ quando aplicável, além de eventual IdP já existente. O analista solicitou esses dados; usar resposta fornecida na conversa se disponível. Não pedir senhas, tokens ou client secret pelo chat. O primeiro responsável recebe papel **OPERATOR na empresa designada**, não um papel ADMIN global inexistente.

Obter issuer+subject do provedor/fluxo autenticado e vincular ao UUID de ator por procedimento controlado. Email não autoriza automaticamente empresa e não substitui subject. Executar `bootstrap-org` dry-run e execução com dados reais confirmados; em seguida provisionar o vínculo específico. Sem concessão genérica a todo login.

Não enviar convite/email/SMS pelo provedor sem autorização explícita para essa comunicação. Preparar cadastro sem envio automático quando suportado e apresentar a ação de convite pronta, com destinatário, para autorização se necessária. O próprio usuário digita senha/MFA no fluxo seguro; não solicitar nem registrar esses valores. Se a prova depender dessa interação, deixar o restante pronto e orientar apenas o passo humano necessário.

## 5. Completar o pacote AWS existente

O Terraform validado no PRM_006 é ponto de partida, não stack pronta. A leitura inicial do analista encontrou os seguintes pontos a completar/verificar:

- Validar conta alvo efetivamente no provider, não apenas declarar `aws_account_id` sem usá-la. State próprio, protegido, com locking e acesso mínimo; não copiar state de outro produto. Arquivos de plan/state podem conter segredos: não versionar ou expor em relatório.
- Provisionar/referenciar ECR próprio, certificado ACM na região do ALB, DNS, banco privado e secrets dedicados; nada de placeholders na aplicação final.
- A execution role deve conseguir ler **somente os secrets referenciados**, e decrypt quando aplicável à chave usada. A policy gerenciada básica de execução não deve ser presumida suficiente para secrets próprios. Separar execution role e task role com privilégios mínimos.
- Adicionar logConfiguration/log group, retenção explícita, correlação e consulta operacional. Sem tokens/cookies/senhas/payloads financeiros nos logs.
- Conferir ferramenta do healthcheck na imagem final: o manifesto usa `curl`; provar disponibilidade ou substituí-lo por comando existente. Diferenciar liveness do processo e readiness para receber tráfego dependente do banco.
- Serviço privado acessível somente pelo ALB. PostgreSQL sem porta pública e liberado somente aos componentes próprios necessários. Planejar resolução DNS, certificados e acesso de saída do backend ao IdP.
- Usar imagem por digest após push ECR, não tag mutável como identidade final da release. Validar plataforma/arquitetura e comportamento no Fargate.
- ALB/serviço devem ter dependências corretas de listener/target group, verificação de deployment e retorno à revisão anterior quando possível. Na primeira publicação não há versão anterior real: o rollback inicial deve retirar o serviço de exposição, preservando dados e diagnóstico.
- Não reutilizar as credenciais migrator no serviço permanente. Separar tarefa de migration/bootstrap e runtime; desativar Flyway automático na tarefa web quando migrations forem executadas separadamente. A tarefa web recebe apenas credenciais necessárias ao runtime, e deve inicializar corretamente nessa configuração.
- Secrets de runtime e migrator separados também no IAM quando necessário: selecionar chaves JSON de um único secret não equivale a isolamento de leitura por chave. Sem senhas no tfvars, comando impresso, imagem ou bundle.

Efetuar testes focados nos ajustes. Não repetir a bateria inteira do PRM_006 sem mudança pertinente. Alteração Java exige verify; alteração frontend exige lint/test/build e prova da tela afetada. Rebuild e smoke test da imagem final se empacotamento mudar.

## 6. Implantação após concordância com o plano

Registrar a concordância do proprietário sobre o plano concreto e custo. Aplicar somente o plano aprovado; se houver drift relevante, recurso de outro produto ou custo novo, preparar a diferença antes de continuar. Não executar terraform destroy em infraestrutura compartilhada.

Sequência operacional:

1. Preparar state, registry, rede/segurança, banco/backup/logs e identidade aprovados. Proteger banco contra exclusão acidental; definir snapshot final e política de retenção.
2. Criar secrets por canal seguro, com papéis separados e sem imprimir seus valores.
3. Gerar/push da imagem e capturar digest ECR. Guardar manifesto com hashes das fontes/artefatos, migrations e resultados de teste, sem exigir commit de todo o monorepo para isso.
4. Executar migrations no banco novo com papel migrator e validar versão/checksums/grants. Provar que runtime não é owner nem possui DDL. Bootstrap real explícito e vínculo do primeiro usuário.
5. Subir ECS, validar logs/readiness e saída OIDC. Realizar validação do certificado por registros dedicados. Criar somente registros necessários ao ActionFinance e à validação de seus certificados, preservando apex/www/api/school e demais nomes.
6. Ativar o host final apenas com TLS e autenticação configurados. Host público pode apresentar entrada; dados/operações continuam protegidos. Nenhum perfil demo ou bypass de autenticação para facilitar a estreia.
7. Fazer a prova de login real com o responsável; conferir empresa autorizada e usuário sem vínculo recusado. Não automatizar senha/MFA fornecida pelo proprietário.
8. Configurar backup e monitoramento reais; comprovar restore em alvo isolado quando aplicável. Se houver dump exportado, proteger armazenamento e acesso. Alertas precisam de destino definido; pedir autorização explícita antes de enviar comunicação de teste a pessoas.

Não criar lançamentos fictícios na empresa real para validar saúde. Testes financeiros continuam em ambiente isolado. Se indispensável teste funcional no destino, usar tenant de homologação separado, identificado e autorizado, sem contaminar a contabilidade real; documentar o procedimento antes.

## 7. Critérios da entrega

Publicação só pode ser declarada quando houver:

- URL pública HTTPS com certificado válido e sem ignorar erros TLS.
- Imagem por digest identificada, serviço saudável e API/SPA servidas na mesma origem; API inexistente não retorna HTML da SPA.
- Login no IdP real, empresa correta, usuário sem vínculo sem dados; tokens demo recusados e CSRF ativo nas operações por sessão.
- Cookie host-only Secure/HttpOnly/SameSite apropriado, logout confirmado e teste de retomada de sessão compatível com o destino.
- Banco privado com migrations/grants corretos, dados reais iniciais confirmados, backup e procedimento de restauração operacional.
- Logs/monitoramento, custo previsto e procedimento de reversão entregues ao responsável.
- Verificação de que DNS/serviços dos demais produtos não sofreram alterações indevidas.

Se alguma dependência externa impedir concluir, nomear exatamente o bloqueio e o que já foi implantado, inclusive recursos que geram custo. Não chamar estado parcial de produção pronta. Não deixar recursos pagos órfãos: descrever manutenção ou reversão do estado parcial dentro do plano aprovado, preservando dados.

## 8. Rastreio e retorno

Salvar este prompt integral em `documents/prompts/ACTIONFINANCE_PRM_007.md`; plano em `documents/operations/ACTIONFINANCE_DEP_001.md`; relatório em `documents/reviews/ACTIONFINANCE_REV_007.md`. Atualizar RUN/índice com procedimentos executados, distinguindo proposta de fato observado.

Retorno deve informar: URL e acesso do usuário; recursos e custo; imagem/digest; identidade real e vínculos (sem segredo); banco/migrations; evidências de HTTPS/login/isolamento; backup/monitoramento; rollback; pendências concretas. Declarar explicitamente se houve publicação e quando. Sem autoaceite e sem PRM_008.

## Adendo 001 — gateway existente

[ACTIONFINANCE_PRM_007_ADENDO_001_GATEWAY](ACTIONFINANCE_PRM_007_ADENDO_001_GATEWAY.md) (30/09/2026). Reavaliar o ALB dedicado face ao ingresso compartilhado real. Não substitui este prompt. Sem PRM_008.

## Adendo 002 — migração autorizada

[ACTIONFINANCE_PRM_007_ADENDO_002_MIGRACAO_ALB](ACTIONFINANCE_PRM_007_ADENDO_002_MIGRACAO_ALB.md). Proprietário: “autorizo”. Execução no mesmo ciclo. Sem PRM_008.

## Adendo 003 — caracteres no nome da empresa

[ACTIONFINANCE_PRM_007_ADENDO_003_ENCODING](ACTIONFINANCE_PRM_007_ADENDO_003_ENCODING.md) (30/09/2026). Corrigir `Loja de PÃ£es` → `Loja de Pães` sem reabrir arquitectura, ingresso ou regras financeiras. Sem PRM_008.

## Referências oficiais para implementação

Consultar versões atuais compatíveis com o provider e bibliotecas usados:

- [Permissões da task execution role ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html)
- [Injeção de secrets no ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data-tutorial.html)
- [Política de criação de usuários Cognito](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-admin-create-user-policy.html)
- [Configuração de clientes Cognito](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-client-apps.html)

Custos e disponibilidade devem ser verificados na região escolhida durante o levantamento; não presumir números a partir deste prompt.
