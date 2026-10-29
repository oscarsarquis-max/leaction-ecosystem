# PRM_009_INC_001 — Complemento de recuperação pública

## Mandato

O proprietário determinou: “precisamos ajustar”. Executar a recuperação do incidente já autorizado. Não devolver apenas instruções para repetir login ou sincronização. Cursor é o executor; não iniciar PRM_010 nem redesign visual neste reparo.

A autorização anterior cobre diagnóstico, correção, testes, publicação e reversão dos componentes afetados dentro do pacote existente. Não solicitar novamente a mesma aprovação. Ampliação de custo, infraestrutura ou uso de dados reais permanece fora do escopo.

## Evidências atuais do proprietário

1. Finance público autenticado como Oscar Sarquis, empresa Padaria de teste público, HOMOLOG: “Sincronização indisponível”, “A Spider não devolveu a listagem”, zero importados. Antes a mensagem era “Não foi possível consultar a Spider”. A mudança de texto não prova recuperação.
2. Monitor público no retorno /oauth/callback: “Acesso negado — O retorno de autenticação é inválido ou já foi usado”.

Não tratar essas evidências como falta de login no Finance. Não reproduzir em documentos ou logs os parâmetros code/state da captura do callback. Causa atual ainda precisa ser demonstrada; os reparos anteriores de WAF/CSP não equivalem ao fechamento destas falhas.

## A. Diagnosticar e corrigir a sincronização

Localizar a tentativa mais recente no AF por empresa e horário, preservando seu identificador. Correlacionar com logs e eventos da Spider e do provider. Identificar a primeira resposta incorreta: status HTTP, tipo de resposta, decisão de contrato/autorização, capacidade selecionada, despacho, resultado do Hub e conversão no AF. Registrar apenas campos necessários e sanitizados.

Verificar o que está efetivamente publicado, não só o código local: digests, configuração, contrato 1.4, registry, binding de tenant/empresa/app/ambiente, credenciais nas fronteiras, endpoint api.actionhub.com.br e schema prm009_public_test. Não presumir que a mensagem genérica do AF prove chegada ao Hub ou à engine.

Comparar o envelope real com o contrato vigente. Distinguir rejeição, indisponibilidade, resposta inválida e lista vazia válida. Corrigir a causa encontrada, sem fabricar resposta READY, substituir por simulador ou criar fallback AF→Pay. Manter a credencial do Pay fora do Finance.

Provar que os quatro itens sintéticos são retornados pela origem e persistidos no AF pelo percurso completo. Repetição não pode duplicar. Preservar dados e histórico da tentativa falha; não limpar tabelas para tornar a demonstração verde.

## B. Diagnosticar e corrigir a autenticação do Monitor

Inspecionar a cadeia pública desde o início de um login novo até criação da sessão: callback registrado, cookies temporários e atributos, state/nonce/PKCE quando aplicáveis, troca de código, domínio/path, políticas de cache e encaminhamento CloudFront/Edge, revisões de Edge efetivamente associadas e eventual processamento duplicado.

Não reusar o callback antigo da captura. Não concluir que a senha está errada nem que o usuário recarregou a página sem evidência. Diferenciar retorno expirado/reutilizado, cookie ausente, state divergente e erro na troca de código em diagnóstico interno sanitizado.

Corrigir sem desabilitar validação de state, TLS, sessão ou autorização. Garantir que páginas/API de autenticação não tenham cache indevido e que a resposta de API sem sessão permaneça 401 JSON quando apropriado, sem quebrar a navegação normal de login.

Depois do login, lista, detalhe e eventos devem carregar pela origem configurada e respeitar o escopo autorizado. Preservar o acesso legítimo ao fluxo canônico e a segregação do fluxo Finance; não resolver escondendo tudo nem abrindo todos os eventos.

## C. Testes e publicação do reparo

Adicionar testes de regressão que reproduzam as causas demonstradas, incluindo configuração pública quando relevante. Construir a partir do conjunto identificado de alterações; registrar commit/digest e versões de frontend/Edge/backend alteradas. Reexecutar os gates dos componentes afetados antes da publicação. Não repetir suites de componentes inalterados sem necessidade.

Aplicar reparo mínimo e validar. Se agravar o serviço ou não restaurar a fronteira afetada, usar rollback seguro previsto, mantendo controles de acesso e dados. Não derrubar engine compartilhada para testar, não esvaziar segredo obrigatório, não remover migrations e não alterar public.orders. Sem mensagens/convites automáticos.

## D. Prova exigida antes de devolver

Executar a jornada nos hosts públicos com sessão legitimamente autenticada:

1. Login novo do Monitor conclui e sua API lista execuções/eventos sem Failed to fetch.
2. Finance na empresa de teste inicia sincronização nova e importa os quatro itens, com referências/valores conferidos contra a origem.
3. “Ver execução na Spider” abre a mesma execução remota: solicitação, empresa autorizada, LIST_PAYMENT_TRANSACTIONS, provider, resposta e devolução.
4. Repetição não duplica; viewer e outra empresa continuam recusados; títulos, baixas e movimentos financeiros existentes permanecem intactos.

HTML 200, readiness UP, ausência de erro no build ou acesso anônimo 401 não substituem esses passos. O link da execução só deve existir quando houver execução remota comprovada; na falha, mostrar referência de suporte da tentativa local sem expor informação sensível.

Se precisar de senha/MFA do proprietário, concluir primeiro o diagnóstico e todos os checks independentes. Solicitar uma única intervenção de login na aba correta, sem pedir credenciais no chat. Depois continuar a validação; não devolver uma nova rodada genérica de tentativas ao proprietário.

## Entrega

Salvar este complemento integral em documents/prompts. Atualizar ACTIONFINANCE_REV_009_INC_001.md com causa demonstrada de cada falha, alterações, testes, versões publicadas, evidências públicas e limites. Manter histórico dos reparos anteriores; não sobrescrever falhas como se não tivessem ocorrido.

Verificar também os registros pendentes de Flyway pós-migrate e remoção da política IAM temporária, sem atribuir a eles a causa deste incidente sem prova. PRM_007 permanece separado.

O aceite continua bloqueado até a jornada pública funcionar. A revisão de layout é uma pendência posterior, sem mudanças de marca neste reparo. Entregar a recuperação comprovada ou um bloqueio externo específico com evidência e ação indispensável.
