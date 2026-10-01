# PRM_009_INC_001 — Recuperar integração e Monitor públicos

Data: 01/10/2026. Prioridade: regressão pública relatada pelo proprietário após implantação autorizada.

## Evidência e estado

As capturas do proprietário mostram:

- Finance autenticado como Oscar Sarquis, empresa Padaria de teste público, HOMOLOG: “Sincronização indisponível”, “Não foi possível consultar a Spider”, zero importados.
- Monitor: “Eventos indisponíveis: Failed to fetch” e “Execuções indisponíveis: Failed to fetch”. O fluxo canônico antes visível deixou de ser utilizável.

Não atribuir o incidente à falta de login com base na sessão diferente do navegador do analista. Não tratar erro de transporte como lista vazia. A causa ainda não foi demonstrada; não afirmar que é CORS, SG ou perda de RAM sem evidência.

O aceite público está bloqueado. Corrigir dentro do escopo da implantação já autorizada; não solicitar novamente a mesma autorização. Cursor continua executor; este documento não declara causa raiz nem execução de reparo.

## 1. Diagnosticar antes de alterar

Preservar horário, revisão/digest e identificador da tentativa AF, sem cookies/segredos. Correlacionar logs do AF, acesso/erro da API Spider, ALB/targets e Monitor/CloudFront. Identificar a URL efetivamente chamada pelo bundle público, a engine de destino e a primeira fronteira que falha.

Investigar separadamente:

1. Tarefa AF → DNS/TLS/rede/ingresso → API Spider → autenticação de satélite → contrato 1.4.
2. Navegador do Monitor → endpoint/proxy público configurado → sessão/Edge → console da mesma engine.

O navegador do proprietário não sai pelo NAT do AF. Liberar o IP do NAT não comprova o acesso do Monitor. Verificar origem efetiva, políticas CloudFront, encaminhamento de headers/cookies e CORS somente conforme a topologia observada. Não abrir SG globalmente nem desativar autenticação para testar.

Comparar configuração e artefatos anteriores/atuais, inclusive bootstrap da empresa, registry/binding, task definitions e variáveis efetivamente carregadas. Health de processo não prova API de negócio nem acesso do navegador.

## 2. Recuperar os dois fluxos

Restaurar primeiro a disponibilidade segura do Monitor e da engine. Aplicar reparo mínimo ou rollback do componente responsável, preservando autenticação e isolamento. Não retornar a acesso amplo como solução para autorização.

Preservar a possibilidade de observar uma nova execução canônica autorizada. Se a política de empresa ocultou execuções canônicas sem companyId, definir autorização explícita apropriada ao fluxo canônico; não inventar empresa nos eventos nem tornar todos os eventos sem empresa públicos. Distinguir evento antigo perdido por restart da incapacidade atual de executar/consultar.

Recuperar também o acesso AF → Spider e concluir a consulta pelo provider FORWARD ao schema de teste. Manter Loja de Pães real fora do binding. Não alterar public.orders, não criar cobranças, não fazer baixas ou movimentações.

Se houver necessidade de reverter integração AF, desabilitar apenas a funcionalidade afetada e preservar login e gestão financeira. Conservar migrations e dados; sem DROP, sem restore destrutivo. Não deixar segredo obrigatório vazio impedindo startup.

## 3. Comprovar no público antes de devolver

Não encerrar com readiness 200, HTML 200 ou 401 anônimo. Exigir:

- Monitor autenticado lê lista/eventos/detalhe sem Failed to fetch e mostra uma nova execução canônica autorizada, ou registra claramente a política aplicada sem erro de transporte.
- Finance autenticado, empresa de teste: sincronização nova conclui e importa os quatro registros esperados, com valores e ausências corretos.
- Link abre a mesma execução no Monitor público; aparecem capacidade, provider e retorno reais.
- Repetição não duplica; outra empresa e usuário sem permissão continuam recusados. Títulos, baixas e movimentos existentes permanecem intactos.

Usar sessão autorizada disponível no navegador. Se login humano for indispensável, solicitar somente essa intervenção, no momento adequado, depois de eliminar as falhas verificáveis sem sessão. Não pedir senha/MFA/cookie nem substituir login por token demo ou bypass. Não transferir ao proprietário uma sequência de testes técnicos sem primeiro verificar os caminhos sob controle do executor.

## 4. UX e encerramento

Em falha de consulta do Monitor, não exibir “Nenhuma transação” como se a busca tivesse concluído vazia. Separar indisponibilidade, vazio real e acesso negado, com opção de tentar novamente.

No Finance, “Ver execução na Spider” não deve prometer uma execução remota existente se o pedido não chegou à engine. Diferenciar tentativa local e execução remota comprovada.

Registrar causa raiz demonstrada, alteração/rollback, versões finais, testes afetados e evidências públicas em ACTIONFINANCE_REV_009_INC_001.md. Validar Flyway após o erro já relatado da tarefa de migrate e registrar remoção da política IAM temporária do bootstrap, sem confundir essas pendências com causa não provada deste incidente.

Salvar este direcionamento integral em documents/prompts e atualizar índice. Preservar histórico e provas locais. PRM_007 separado; sem PRM_010. Entrega continua sem aceite até a jornada pública funcionar para o proprietário. Se bloqueado, relatar fronteira exata, evidência e dependência indispensável, sem declarar recuperação parcial como conclusão.
