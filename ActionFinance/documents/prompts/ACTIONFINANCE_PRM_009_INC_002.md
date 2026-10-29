# PRM_009_INC_002 — Sincronização operacional reprovada no público

Data: 02/10/2026. Continuação do incidente PRM_009; sem PRM_010.

## Evidência do proprietário

Finance público autenticado como Oscar Sarquis, empresa Loja de Pães, ambiente PRODUCTION: “Sincronização indisponível”, “Não foi possível consultar a Spider”, importados/atualizados/em revisão = 0. Monitor público: nenhuma transação no recorte, ambiente não afirmado. Essas capturas reprovam a afirmação de que só faltava sessão humana para concluir.

Não atribuir a falha a login, live_mode ausente ou necessidade de APPLY histórico sem prova. Os nove registros devem poder entrar em revisão. A tela vazia do Monitor não prova sozinha ausência na engine nem perda por RAM. A causa desta tentativa ainda é desconhecida.

## Ação imediata autorizada

1. Localizar no AF a tentativa mais recente da Loja correspondente ao relato, por empresa, usuário e horário, sem imprimir dados pessoais desnecessários. Registrar run ID, correlação, início/fim, estado e erro técnico sanitizado. Se a mensagem genérica ocultou a causa, melhorar o diagnóstico interno e a referência de suporte, sem expor segredos ao usuário.
2. Rastrear a mesma tentativa desde a tarefa AF efetivamente publicada: URL/configuração carregada, DNS/TLS, egress, SG/WAF/ALB, autenticação satélite, schema/contrato PRODUCTION, binding e seleção da capacidade. Mostrar a primeira fronteira que falhou com evidência. Não presumir que WAF/configuração continuam corretos por terem funcionado para HOMOLOG anteriormente.
3. Se o pedido chegou à engine, seguir provider, URL/método/rota reais, credencial e resposta Hub, validação do envelope e persistência de items/reviews. Confirmar que AF/Spider/Hub públicos executam versões compatíveis; teste local ou loopback no Hub não valida esse percurso.
4. Separadamente, verificar se a correlação existe no store/eventos e se o Monitor consulta a mesma engine com o vínculo da Loja. Conferir lista, detalhe e eventos sob autorização real; não desativar filtros nem criar eventos para preencher a tela.

## Correção e regressão

Aplicar correção mínima da causa comprovada, com teste que reproduza a falha e registro das versões/configurações alteradas. A autorização de recuperação/publicação dentro do escopo continua válida. Preservar dados, histórico de tentativas e controles de acesso; sem novos recursos faturáveis, cobrança, pagamento, simulação disfarçada ou escrita manual dos recebimentos no AF.

Não ampliar este incidente para redesign, novos produtos ou reparo histórico do Pay. Preservar a regressão de todo o módulo Pay exigida anteriormente se houver alteração nele. Não apagar dados nem reiniciar indiscriminadamente serviços compartilhados. Preservar evidências da engine antes de reinício necessário.

## Prova obrigatória de conclusão

Confirmar, com contexto público autorizado da Loja, uma execução nova pelo fluxo Finance → Spider → Hub de produção → Spider → Finance. Demonstrar os registros da origem importados, inclusive revisões, valores cobrados e valor pago ausente quando não comprovado. Repetição não duplica; títulos/baixas/movimentos permanecem intactos.

Abrir o deep link dessa execução no Monitor e mostrar as fases reais, detalhes e origem, mantendo o formato anterior. O requisito da canônica original permanece separado e não dispensado.

Usar sessão legitimamente disponível; não extrair cookies nem contornar OIDC. Se nova intervenção humana for de fato indispensável, concluir antes os checks independentes, demonstrar que o bloqueio técnico anterior foi removido e solicitar apenas o login necessário. Não declarar novamente “só falta login” sem essa comprovação.

Não aceitar health 200, HTML publicado, teste mockado ou chamada isolada do Hub como prova da jornada. Entregar causa raiz, reparo, regressão e evidência ponta a ponta; se impedido, indicar a fronteira e dependência exatas.

Salvar prompt em documents/prompts e relatório em documents/reviews/ACTIONFINANCE_REV_009_INC_002.md, referenciando o INC_001 sem sobrescrever o histórico. Aceite continua NÃO. APPLY histórico e pendências PRM_007 permanecem separados.
