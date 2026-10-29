# ActionFinance correção prioritária do comando Sair

Identificador: ACTIONFINANCE_PROMPT_CORRECAO_LOGOUT_009. Data: 05/10/2026. Destinatário: Cursor. Documento novo e independente; não altera prompts anteriores. O sufixo 009 identifica esta sequência de instruções e não reabre nem substitui ACTIONFINANCE_PRM_009 de integração.

## Incidente e prioridade

O proprietário relata que clica em Sair e não consegue encerrar o acesso em https://actionfinance.actionhub.com.br/receivables. A captura mostra a aplicação ainda autenticada. Há um 404 de favicon e um aviso de inicialização no console; nenhum deles comprova a causa da falha de logout. Não atribuir culpa a esses avisos, ao Cognito, à senha ou ao usuário sem rastrear o fluxo.

Captura: C:\Users\OSCARS~1\AppData\Local\Temp\codex-clipboard-d82931fa-af20-468e-a6d4-3701cb3bc905.png. Se indisponível, usar a descrição e reproduzir a versão atual. Priorizar esta falha funcional de sessão sobre os ajustes de composição ainda em andamento.

## Diagnóstico obrigatório

Confirmar assets e versão pública. Preparar navegador acessível ao executor e solicitar somente login humano se necessário, sem senha/MFA/cookies no chat. Não pressupor que a sessão do Chrome do proprietário está disponível em outro perfil.

Reproduzir clique e acionamento por teclado de Sair. Conferir se o evento chega ao handler, se uma camada intercepta o controle, se proteção de formulário sujo bloqueia a saída sem diálogo visível, se há navegação padrão de link, exceção ou promise não tratada. Depois rastrear a obtenção de CSRF e a requisição de logout realmente emitida, com método, caminho, horário, status e resposta sanitizados. Não registrar valores de tokens ou cookies.

Distinguir quatro possibilidades com evidência:

1. O clique não dispara o fluxo.
2. O pedido sai, mas o servidor o recusa ou não responde.
3. O servidor encerra a sessão, mas a SPA mantém dados/estado autenticado.
4. A sessão termina e o redirecionamento automático reinicia OIDC, recriando o acesso pela sessão ainda existente no provedor.

Não presumir que seja um desses casos sem observar. Registrar a fronteira e o código responsáveis e criar teste que reproduza a causa real.

## Comportamento esperado

Sair deve ser um comando acessível, preferencialmente botão type=button com apresentação discreta se desejado. Apresentar estado de processamento e evitar acionamentos simultâneos. Se houver rascunho sujo, pedir confirmação visível e acessível; recusa mantém página/dados, aceite prossegue.

O logout AF deve ocorrer pelo mecanismo servidor existente, preservando CSRF e invalidação da sessão. Não trocar por GET mutável, desabilitar CSRF, apagar apenas sessionStorage/localStorage ou esconder a interface para aparentar encerramento.

Após encerramento confirmado: limpar estado/dados sensíveis em memória do contexto autenticado e destinos transitórios que causem reentrada automática. Mostrar estado de saída com ação explícita Entrar novamente. A regra de acesso direto ao Cognito para entrada anônima normal não deve produzir loop imediatamente após logout explícito.

Manter a distinção entre sessão ActionFinance e sessão Cognito. Este corretivo deve garantir que Sair encerre a sessão AF e não faça login novamente sozinho. Não expandir silenciosamente para logout global de outros produtos nem modificar o pool. Se a implementação já prevê logout do provedor, conferir URLs permitidas e o alcance antes de preservá-lo; registrar a semântica efetiva.

Em recusa 403 ou falha de transporte, não apresentar saída concluída sem prova. Informar falha e permitir recuperação controlada. Se o resultado for desconhecido, verificar o estado da sessão no endpoint autorizado existente; não simular encerramento nem criar um loop de retry. Revalidar CSRF/sessão conforme protocolo vigente.

## Provas exigidas

- Sessão autenticada: identidade/contexto disponível antes do clique. Sair válido: endpoint protegido responde 401 depois, e dados financeiros não continuam acessíveis por API sem reautenticação.
- SPA chega ao estado de saída e permanece nele sem reiniciar OIDC automaticamente. Recarregar esse estado não recria loop.
- Voltar no navegador ou usar outra aba aberta não permite novas operações autenticadas com a sessão encerrada. Revalidar no retorno à aba para evitar apresentar dados antigos como sessão ainda ativa. Distinguir conteúdo já renderizado em cache de acesso servidor; tratar ambos sem prometer invalidação global inexistente.
- Entrar novamente é ação explícita e funciona conforme sessão do provedor, com destino interno permitido. Nunca reutilizar callback antigo.
- CSRF ausente/inválido é recusado e não encerra uma sessão válida. Falha/rede e proteção de rascunho têm comportamento correto em ambiente controlado.
- Testar mouse/teclado em desktop e toque/viewport mobile, incluindo a largura reduzida pela abertura do DevTools observada na captura.

Testes unitários/mocks apoiam a correção, mas não substituem um logout autenticado real no host público. Não transferir essa suíte ao proprietário; ele participa apenas do login/desafio necessário. Agrupar a prova para evitar pedidos repetidos desnecessários de autenticação.

## Limites e publicação

Corrigir o código necessário de frontend/backend dentro do fluxo existente, com testes pertinentes. Não alterar finanças, dados de produção, vínculos de empresa, credenciais, Hub/Pay, Panne ou Spider. Não disparar recuperação de senha nem convite. Não modificar controles de segurança para fazer o botão funcionar.

Publicar pelo canal de correção autorizado após gates, registrando versão/digest e rollback. Se houver alteração Java/security, executar verificações backend adequadas; teste frontend não é prova dessa mudança. Não reiniciar Spider nem reaplicar branding Cognito sem necessidade demonstrada. Corrigir favicon separadamente se conveniente, sem apresentá-lo como causa do incidente.

## Entrega

Criar ACTIONFINANCE_REV_CORRECAO_LOGOUT_009.md com reprodução, causa, correção, semântica de saída AF/Cognito, evidências antes/depois, versão pública e resultados por ambiente. Copiar este prompt para documents/prompts como documento novo e indexar.

Não afirmar “logout passou” por redirecionamento ou ausência visual de dados apenas. A prova exige sessão servidor encerrada, ausência de reentrada automática e estado da interface coerente. Aceite continua com analista/proprietário; demais pendências permanecem separadas.
