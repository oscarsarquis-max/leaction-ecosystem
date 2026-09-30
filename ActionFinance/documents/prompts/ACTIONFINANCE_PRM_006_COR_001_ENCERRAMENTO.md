# PRM_006_COR_001 — Parecer focado e complemento de encerramento

Data: 29/09/2026. Analista: Codex. Executor: Cursor.

## Parecer sobre o retorno

O bloqueio da imagem e do ensaio HTTPS foi superado nas evidências apresentadas. O analista leu o relatório, journey-log, resumo Failsafe (43 testes, zero falhas/erros/skips), código de autorização por empresa, validação de produção, cliente de logout, script de build e Dockerfile. Inspecionou capturas da entrada e da baixa parcial móvel. Não reexecutou testes ou containers.

Aceitos neste recorte: correção da autorização por empresa, endurecimento da configuração de produção, imagem de runtime construída e ensaiada, atributos do cookie observados e jornada principal OIDC nas três larguras. Preservar as provas existentes. A imagem local informada é `sha256:cb6736f5b16b6860870543c332b76ab1b330a6eeaee44a3f4d75e833ceb523a1`, sem digest remoto. A inspeção de capturas não é aprovação estética do proprietário.

O aceite integral do PRM_006 permanece pendente somente dos três pontos abaixo. Não reabrir a lista completa C1–C6 nem iniciar PRM_007. Este complemento pertence ao mesmo corretivo.

## 1. Sessão após reinício real do processo

O relatório diz que o restart de JVM não foi refeito e cita testes de revogação como cobertura. Revogação em processo ativo não prova persistência/recuperação de sessão após restart.

No ambiente descartável já disponível, autenticar usuário provisionado estável, registrar ator e identificador de empresa sem expor cookie/token, reiniciar somente o processo/container da aplicação e manter banco/IdP/navegador. Após readiness, comprovar que a sessão anterior recupera o mesmo ator e escopo sem novo login nem reprovisionamento. Depois revogar um vínculo, comprovar bloqueio no próximo pedido e confirmar logout efetivo.

Não confundir entrar novamente e provisionar um novo subject do mock com recuperar a sessão anterior. Não precisa repetir toda a jornada financeira nas três larguras para essa prova.

## 2. Upgrade e restauração das tabelas novas

Aplicar V1–V7 em banco vazio prova instalação limpa; não substitui atualização de base V5 nem restauração. O script de backup inspecionado ainda exige apenas V1–V5 e verifica principalmente tabelas financeiras. Não foi localizada evidência de restore cobrindo identidade/sessão deste ciclo.

Em ambiente descartável:

- Criar base até V5 com fatos financeiros de teste, registrar checksums e valores, atualizar até a versão atual e comprovar preservação de títulos, baixas, movimentos e históricos.
- Acrescentar identidade/vínculos/auditoria de teste, fazer backup e restaurar em outro banco descartável. Verificar dados, owners, grants e Flyway validate, incluindo tabelas V6/V7. Não depender de ACLs reconstruídas manualmente só para as tabelas antigas; validar o procedimento completo de recuperação.
- Comprovar que runtime lê as novas tabelas necessárias, mantém os limites de escrita estabelecidos e não possui DDL ou DELETE sobre fatos/auditoria. Validar limpeza de sessão conforme política documentada.
- Aplicar o procedimento de invalidação de sessões após restore operacional: cookie anterior deixa de autenticar, dados financeiros/identidades/vínculos/auditoria permanecem. Essa prova é distinta do restart normal, que deve preservar sessão.

Não restaurar sobre volumes de desenvolvimento ou produtos existentes. Registrar comandos e resultados sem senhas. Corrigir scripts/documentação apenas onde necessário.

## 3. Cadastro rápido pela interface

O ensaio contornou por API o cadastro de contraparte/categoria porque o diálogo não enviou POST. Isso deixa uma falha ou limitação da automação sem diagnóstico. Não fechar como “comprovado” esse trecho.

A inspeção encontrou `QuickCatalog` renderizado dentro do `<form>` do título em `App.tsx`; ele contém outro `<form>`. `Modal.tsx` renderiza o dialog no mesmo local, sem portal. Portanto há formulários aninhados no DOM. Investigar isso como causa concreta, sem presumir que a falha é exclusiva de headless. Corrigir a estrutura, colocando o diálogo fora do formulário pai ou usando portal apropriado; preservar foco, Escape, retorno ao acionador e rascunho do título. Não redesenhar o modal.

Provar no navegador com OIDC: abrir Novo recebível com campos do título ainda incompletos → cadastrar contraparte pelo diálogo → selecionar automaticamente o item criado → cadastrar categoria pelo diálogo → completar e registrar o título. Salvar no diálogo não pode exigir validação do título pai nem submeter o título. Cancelar/Escape preservam os campos do título. Conferir POST e persistência reais, sem criação via API como substituto da ação de UI. Cobrir desktop e 360 px; testar regressão de foco/submit no frontend.

## Entrega e limites

Manter escopo em ActionFinance, versões e marca. Sem novas integrações, infraestrutura remota, DNS, commit/push ou ativação pública. Não modificar dados reais. Não reexecutar verificações não afetadas só para aumentar contagens.

Se houver alteração de código, executar testes pertinentes e gerar/ensaiar a imagem correspondente à versão final, registrando novo image ID e hash do JAR. Não atribuir à imagem anterior as correções posteriores. Para mudança só frontend, lint/test/build e ensaio do fluxo afetado; para mudança Java/persistência, verify com ITs sem skip.

Salvar este complemento em `documents/prompts`, adicionar os resultados ao `ACTIONFINANCE_REV_006_COR_001.md` e indexar. Apresentar tabela com três linhas: restart, upgrade/restore, cadastro rápido; prova, resultado e caminho da evidência. Preservar relatório original e distinguir o aceite parcial acima do aceite integral ainda pendente.

Parar para revisão focada desses três pontos. IdP real, DNS e AWS continuam separados como próximos passos de publicação; não são motivo para deixar estes ensaios locais incompletos.
