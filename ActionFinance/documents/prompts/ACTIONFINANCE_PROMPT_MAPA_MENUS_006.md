# ActionFinance organização definitiva do recorte em menus e submenus

Identificador: ACTIONFINANCE_PROMPT_MAPA_MENUS_006. Data: 02/10/2026. Destinatário: Cursor. Documento novo, independente e completo para esta instrução. Preservar os anteriores como histórico.

## Decisão do proprietário

Eliminar o termo e o destino “Mais”. Não existe uma área de negócio com esse nome. Organizar a navegação em menus e submenus explícitos, dispostos em duas barras horizontais paralelas, uma abaixo da outra. Sem menu suspenso, dropdown de navegação, painel lateral, drawer ou modal de destinos.

Esta instrução prevalece sobre alternativas anteriores de manter Mais, criar uma página Mais ou usar barra inferior mobile. Não desfaz os requisitos de correção da tela azul, acessibilidade, proteção de formulário e preservação financeira.

## Mapa a implementar com as funções atuais

| Menu principal | Submenu | Destino e significado |
|---|---|---|
| Recebimentos | A receber | Lista de contas a receber existente, com seus estados e filtros. Rota atual /receivables preservada. |
| Recebimentos | Transações importadas | Lista externa hoje em /pay-receipts; identificar ActionHub Pay dentro da página como sistema integrado. Importação não é liquidação. |
| Pagamentos | A pagar | Lista de contas a pagar existente. Rota /payables preservada. |
| Contas | Contas financeiras | Lista existente /financial-accounts; selecionar conta abre seus movimentos/detalhe. |
| Cadastros | Clientes e fornecedores | Cadastro de contrapartes existente em /catalogs/counterparties. Conferir resolução efetiva no router. |
| Cadastros | Categorias | Cadastro existente em /catalogs/categories. Conferir resolução efetiva no router. |

Confirmar as rotas no código antes de alterar links. Se os cadastros hoje compartilham uma página, os submenus devem selecionar a seção correspondente de forma real, acessível e endereçável; não criar dois links indistinguíveis para a mesma página sem seleção. /catalogs continua compatível e encaminha a um destino claro.

É aceitável um menu ter apenas um submenu enquanto a capacidade é limitada. Não preencher a barra com ações de criação ou funções inventadas. Menu Contas não deve sugerir fluxo de caixa/transferências/conciliação ainda ausentes.

## Ações pertencem às páginas

| Contexto | Ação e local |
|---|---|
| A receber | Nova conta a receber, junto ao título da lista. |
| A pagar | Nova conta a pagar, junto ao título da lista. |
| Detalhe de título | Registrar recebimento ou Registrar pagamento, conforme direção e permissões. |
| Registro financeiro existente | Estornar registro, com confirmação e motivo, sem sugerir devolução bancária. |
| Transações importadas | Sincronizar, com escopo da conexão/empresa explícito. |
| Contas financeiras | Nova conta; selecionar uma conta para consultar movimentos. |
| Cadastro | Criar/editar o cadastro correspondente, segundo permissões existentes. |

Retirar “Registrar recebível”, “Registrar pagável” e cópias desses destinos de qualquer navegação global. Não repetir A receber/A pagar em outro menu. Rótulos de compromisso e liquidação devem permanecer distintos: criar conta não registra dinheiro recebido/pago.

## Estrutura visual

Manter faixa fina #1603AD com marca branca oficial horizontal. Abaixo, barra principal sobre superfície clara: Recebimentos | Pagamentos | Contas | Cadastros. Logo abaixo, barra contextual em azul muito claro com os submenus da área selecionada. Indicadores de seleção coerentes nos dois níveis; texto escuro legível e contraste medido. Não usar branco sobre lilás claro.

As barras permanecem no fluxo da página e não cobrem os dados. Ao escolher menu principal, navegar ao primeiro submenu funcional da área; se futuramente houver restauração do último destino, fazê-la de modo explícito e testado. Deep links e recarga devem reconstruir ambos os níveis pela rota. Não reaplicar a seleção inicial contra escolhas posteriores do usuário.

No celular, manter os dois níveis consecutivos. Pode abreviar Recebimentos/Pagamentos para Receber/Pagar, conservando significado. Se necessário, rolagem horizontal confinada a cada barra, com indicação de continuidade e item ativo visível. Não esconder destinos sob “Mais”, reticências ou hambúrguer; não duplicar o menu em uma barra inferior. Verificar que a página não ganha overflow horizontal e que os controles continuam acessíveis ao toque/teclado.

## Evolução futura não é destino disponível

Recebidos/Pagos exigem visões de liquidações registradas. Não gerar essas abas com transações aprovadas pelo Pay ou títulos filtrados de modo que escondam liquidações parciais. Movimentos consolidados, Integrações, Transferências, Conciliação e Fluxo de caixa só entram em menus próprios quando houver jornadas funcionais especificadas e entregues. Não criar telas vazias para aparentar amplitude do sistema.

Transações importadas é um conceito amplo, mas a primeira fonte efetiva continua ActionHub Pay. Não anunciar múltiplos conectores ou filtros sem dados. Origem comercial, sistema integrado, processador, método e empresa não são equivalentes.

## Correção técnica e provas

Eliminar o mecanismo do antigo Mais e investigar/documentar a tela azul relatada. Remover overlays, listeners, estados de foco/inert/scroll que pertenciam exclusivamente a esse menu. Não remover proteção de modais legítimos ou esconder erros com reload/catch vazio.

Testar em 360, 768 e 1280 px: todos os pares menu/submenu, navegação repetida, links antigos, recarga, Voltar/Avançar, foco, rolagem e contraste. Conferir formulário sujo com saída recusada e aceita. Validar viewer/operator e contexto de empresa sem alterar autorizações reais de produção.

Executar lint, testes pertinentes e build. Publicar somente a correção do recorte pelo canal vigente autorizado, com imagem anterior preservada para rollback. Verificar a versão final e a navegação autenticada pública. Se houver necessidade de login humano, preparar a aba acessível ao executor e pedir apenas autenticação, sem senha/MFA/cookies no chat.

Não escrever fatos financeiros em produção para demonstrar navegação. Sem alterações em banco, Cognito, Hub/Pay, Panne ou Spider; não reiniciar engine. Bugs financeiros encontrados devem ser relatados separadamente, sem expansão silenciosa de escopo.

## Entrega

Salvar novo relatório ACTIONFINANCE_REV_MAPA_MENUS_006.md com mapa final de rotas, capturas desktop/mobile, diagnóstico da tela azul, resultados, versão publicada e limitações. Copiar este prompt para documents/prompts como documento novo e indexar. Referenciar 003/004/005 como histórico, sem alterá-los. Não duplicar desenvolvimento: consolidar a implementação ainda em andamento conforme esta decisão mais recente.

Aceite permanece com analista/proprietário. Não encerrar PRM_009, prova Spider, canônica histórica, Pay, APPLY ou PRM_007 por uma correção de navegação.
