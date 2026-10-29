# ACTIONFINANCE_PRM_007 — Autorização de continuidade

Data: 30/09/2026. Orientação do analista ao Cursor.

## Concordância do proprietário

O proprietário respondeu **“concordo sim...”** ao plano de publicação apresentado: infraestrutura existente na conta corporativa, serviço próprio do ActionFinance, RDS próprio, Cognito dedicado e estimativa inicial de **US$ 65–80/mês, mais impostos**. A concordância com os recursos e esse gasto está registrada. Não pedir novamente a mesma aprovação.

Este documento complementa o PRM_007; não é PRM_008. O plano aprovado é `documents/operations/ACTIONFINANCE_DEP_001.md`, de 30/09/2026. O valor é estimativa para as premissas descritas, não teto técnico automático da AWS.

## Ação autorizada agora

Prosseguir com o PRM_007: conferir plano Terraform real, provisionar os recursos do ActionFinance previstos no plano e preparar a publicação restrita em `actionfinance.actionhub.com.br`.

1. Revalidar conta `253137917703`, região `us-east-2`, VPC/subnets/rotas e recursos compartilhados referenciados. Gerar e inspecionar o plan antes de cada etapa de apply. O plan de leitura não depende de nova aprovação de gasto.
2. Confirmar que os recursos, dimensionamento e custos permanecem aderentes ao DEP_001, sem exclusão/substituição ou modificação operacional de outros produtos. Se houver divergência material de custo/escopo, apresentar somente essa diferença para decisão; não repetir aprovação do plano inteiro. Não criar NAT Gateway ou adotar outro desenho mais caro silenciosamente.
3. Aplicar state e fundação próprios: registry, segurança, ALB/certificado, RDS privado, secrets, identidade e logs, conforme dependências. Preservar VPC/NAT/endpoints e serviços compartilhados. Validar referências e permissões, não confiar só em terraform validate.
4. Construir e publicar imagem no ECR autorizado, registrando digest e correspondência com fontes/testes. O push da imagem está autorizado; commit/push Git continua fora do escopo.
5. Executar bootstrap técnico de banco/roles e migrations com credenciais próprias, verificando Flyway e grants. Serviço web sem secret migrator e sem DDL. Nunca copiar dados ou senhas demo.
6. Preparar serviço, certificado e configurações reais de OIDC. Aguardar os dados reais necessários ao cadastro da empresa/operador; não inventar identificadores nem criar empresa fictícia para contornar a pendência.
7. Manter o alias público desativado até os critérios do PRM_007: TLS, migrations, autenticação real e primeiro operador provisionado. A criação dos registros de validação do certificado próprios faz parte da infraestrutura autorizada. Preservar apex/www/api/school e outros nomes existentes.
8. Assim que os dados reais forem fornecidos, continuar dentro deste mesmo ciclo, sem nova aprovação geral. Confirmar login com participação humana para senha/MFA, sem solicitar segredos no chat. Validar operação, backup/monitoramento e reversão conforme PRM_007 antes de declarar publicação concluída.

## Dados e comunicações pendentes

Dados confirmados e corrigidos pelo proprietário após a emissão deste adendo:

- **Identificador de login do operador do ActionFinance: `admin@actionhub.com.br`.** É somente login, sem caixa postal. Esta indicação substitui `admin@lojadepaes.com.br` para o primeiro acesso ao financeiro. Não enviar mensagens a nenhum desses dois endereços.
- Empresa gerida inicialmente: **Loja de Pães**. Ainda não possui CNPJ. Usar esse nome de exibição; não inventar razão social ou identificação fiscal. A ausência de CNPJ não bloqueia esse cadastro inicial ou o acesso.
- Vincular o operador confirmado como OPERATOR à Loja de Pães. O domínio do e-mail não transforma a empresa gerida em ActionHub nem concede acesso global.
- **Endereço central de comunicação: `oscar@oscarsarquis.com.br`.** O proprietário determinou centralizar nele as comunicações. Convite de acesso, verificação/recuperação de conta e alertas operacionais deste produto devem usar exclusivamente esse destinatário. Essa instrução autoriza as comunicações necessárias à implantação para esse endereço; não repetir pedido de autorização para o convite já direcionado pelo proprietário. Não imprimir senhas/códigos no chat ou em logs.
- Separar tecnicamente username/login do atributo de e-mail de contacto no IdP. Preservar login `admin@actionhub.com.br` e e-mail real `oscar@oscarsarquis.com.br`; confirmar que configuração do pool, tela de entrada e recuperação suportam essa combinação antes de provisionar. Não configurar silenciosamente um modo de login exclusivamente por e-mail que obrigue a substituir o identificador solicitado. Não marcar e-mail como verificado sem o procedimento de verificação aplicável. O vínculo local continua por issuer+subject, nunca por coincidência de e-mail.

A autorização de gasto continua sendo o “concordo sim”. A autorização e o destino das comunicações decorrem da instrução posterior de centralização em `oscar@oscarsarquis.com.br`, conforme acima. Antes de enviar, conferir o destinatário efetivo do provedor e dos alertas. Não ampliar destinatários nem modificar comunicações de outros produtos neste ciclo.

Primeiro usuário com papel OPERATOR na empresa indicada; não criar ADMIN global. O próprio executor obtém issuer+subject do provedor real e realiza o vínculo controlado. Não transferir ao proprietário a tarefa de descobrir esses identificadores técnicos.

## Preservar limites de produto

Não abrir integração neste ciclo. A primeira integração após publicação será ActionHub Pay, via Spider, para pagamentos e recebimentos da Loja de Pães. O ActionHub Pay centraliza a execução de pagamentos de todas as origens. O Panne mantém compras e estoque físico da loja; o ActionFinance centraliza a gestão. Nenhuma obrigação importada paga automaticamente.

## Rastreio e retorno

Copiar este adendo para `documents/prompts`, registrar concordância em DEP_001 e REV_007 e indexar. Não atribuir aceite técnico ao executor. Relatar recursos efetivamente criados, custos em curso, digest, provas e pendências. Sem segredos em logs/relatórios/state público.

Se houver bloqueio, informar exatamente o insumo faltante e continuar tarefas independentes. Recursos já criados geram custo mesmo antes do DNS: declarar esse estado, manter acompanhamento e não deixar itens órfãos. Não destruir banco ou recursos compartilhados para limpar uma implantação parcial.

Ao concluir a publicação ou alcançar um bloqueio real dependente do proprietário, devolver o resultado do PRM_007. Não emitir PRM_008.
