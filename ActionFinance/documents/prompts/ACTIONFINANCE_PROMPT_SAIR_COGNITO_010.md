# ActionFinance sair e retornar ao formulário Cognito

Identificador: ACTIONFINANCE_PROMPT_SAIR_COGNITO_010. Data: 05/10/2026. Documento novo e independente destinado ao Cursor. O número é desta sequência de instruções, não emissão do ciclo financeiro PRM_010.

## Decisão do proprietário

O proprietário confirmou que conseguiu sair, mas rejeitou a tela intermediária “Você saiu do ActionFinance” com botão “Entrar novamente”. Após Sair, o destino deve ser diretamente o formulário Cognito personalizado do Finance. Esta orientação substitui o estado intermediário de saída exigido no corretivo anterior; preserva a obrigação de encerrar a sessão e impedir reautenticação automática.

Não alterar ou sobrescrever prompts anteriores. Não interpretar o relato como aceite integral de segurança ou do produto.

## Resultado esperado

Sair → encerrar sessão ActionFinance com CSRF → encerrar a sessão de navegador Cognito pertinente ao acesso Finance → abrir o formulário personalizado aguardando nova autenticação. Nenhum botão intermediário para chegar ao formulário. Nenhuma volta automática à área autenticada pela sessão anterior do provedor.

A tela de sucesso intermediária deve sair do percurso normal. Estado de falha recuperável ainda é necessário se o encerramento/redirecionamento falhar, sem fingir sucesso ou criar loop.

## Desenho técnico seguro

Inspecionar a implementação atual e a configuração real do client/domínio Finance antes da alteração. Distinguir POST /logout da aplicação, com CSRF, do endpoint HTTPS GET /logout do domínio Cognito. Não converter logout local em GET mutável nem desativar proteção.

Referência oficial consultada em 05/10/2026: https://docs.aws.amazon.com/cognito/latest/developerguide/logout-endpoint.html . A AWS documenta saída no navegador e redirecionamento para destino permitido ou login. Confirmar compatibilidade com o Hosted UI clássico existente. Não pressupor que esse mecanismo encerra sessões em provedores externos.

Preferir fluxo que, após logout local confirmado, passe pelo logout Cognito e por uma rota interna permitida que inicie uma NOVA autorização OIDC gerenciada pelo backend, sem tela intermediária. Preservar state/nonce novos e a requisição de autorização armazenada pelo Spring. Não construir URL de login com state inventado na SPA nem reutilizar callback/code anterior. Se escolher redirecionamento direto do logout Cognito ao login, demonstrar a integração correta com o estado OIDC esperado no backend.

Verificar Allowed sign-out URLs e callbacks do client Finance. Qualquer ajuste necessário deve ser mínimo, exato e reversível; não liberar curingas ou destinos externos. Não usar parâmetro arbitrário de usuário como URL de retorno. Distinguir callback de login, retorno de logout e página interna pretendida.

O proprietário solicitou encerrar e voltar ao formulário; isso inclui resolver a sessão Cognito que antes recriava o acesso. Verificar se o domínio/client compartilha a sessão de navegador com outros aplicativos: não afirmar isolamento por client_id sem verificar. Evitar GlobalSignOut, revogação global de dispositivos ou alteração em outros pools/produtos. Se houver impacto compartilhado inevitável, preparar a alternativa concreta e explicitar antes de ampliar o alcance.

Manter o branding atual, sem reaplicar CSS/logo ou trocar plano. Não criar formulário de senha no Finance, iframe ou tela que imite Cognito. Login, recuperação e MFA continuam no provedor.

## Casos de falha e contexto

Preservar confirmação de rascunho sujo; recusa não sai, aceite prossegue. Evitar cliques simultâneos e informar processamento. Recusa CSRF ou erro de rede não pode virar saída concluída. Se a sessão AF foi encerrada, mas o Cognito falhar, indicar o estado real e oferecer repetição segura, sem restaurar dados autenticados.

Limpar destino transitório obsoleto e evitar reentrada silenciosa. O acesso normal por deep link continua podendo guardar destino interno autorizado; logout explícito não deve reciclar indevidamente uma autorização anterior. Não apagar a proteção contra loops sem substituí-la por uma sequência correta.

## Prova obrigatória

1. Sessão AF autenticada real → clique Sair → logout local aceito → API protegida 401 antes de qualquer nova autenticação.
2. Browser chega ao formulário Cognito personalizado sem clique intermediário e permanece aguardando autenticação. Capturar o formulário real, não apenas 302 ou página local.
3. Recarregar e usar Voltar não permite requisições financeiras autenticadas com a sessão anterior. Não confundir cache visual com acesso servidor; tratar apresentação obsoleta ao retomar a aba.
4. Nova autenticação completa pelo formulário funciona sem erro de state/callback e retorna ao destino interno definido.
5. Exercitar desktop/mobile, rascunho aceito/recusado e falhas controladas. Testar CSRF e URL de retorno inválidos sem afetar serviços produtivos.

Preparar a aba acessível ao executor e pedir somente login/MFA quando necessários. Não pedir senha, códigos ou cookies no chat; não disparar recuperação/e-mail. O executor conduz e documenta o restante da prova. A observação humana “saiu” não substitui a verificação de sessão servidor.

## Publicação e entrega

Executar gates pertinentes ao código alterado; se houver backend/security, incluir testes adequados além do frontend. Publicar pelo canal corretivo autorizado, com versão/digest, configuração anterior e rollback. Não alterar dados financeiros, Spider, Hub/Pay ou Panne, nem reiniciar engine.

Criar ACTIONFINANCE_REV_SAIR_COGNITO_010.md com sequência implementada, alcance da saída, configurações alteradas, evidências públicas e limitações. Copiar este prompt como novo arquivo para documents/prompts e indexar. Referenciar o corretivo 009 como histórico, sem modificá-lo.

Aceite permanece com analista/proprietário. Não encerrar outros ciclos a partir desta correção.
