# ACTIONFINANCE_PRM_009_CONTINUIDADE_001 — Executar o percurso real e a demonstração

Data: 01/10/2026.

## Parecer e mandato

O analista leu ACTIONFINANCE_REV_009 e o guia do proprietário. A entrega é intermediária; o aceite do PRM_009 permanece pendente. Testes isolados não substituem o requisito central de ver o Finance passando pela Spider até o código real do Hub.

Continuar o mesmo PRM_009, sem iniciar PRM_010. Preservar a implementação e os testes úteis; corrigir defeitos encontrados no percurso. Este documento não atribui aceite técnico integral ao código ainda não revisado ponta a ponta.

Hub e Monitor recusarem conexão significa que os serviços precisam ser preparados e iniciados. Isso, por si só, não constitui dependência externa que exija devolver o trabalho ao proprietário. A preparação local já está autorizada pelo PRM_009.

## 1. Preparar o ambiente

Inspecionar scripts, dependências, configuração e propriedade das portas. Subir o código real do gateway Hub com PostgreSQL descartável, o provider em FORWARD, a Spider, seu Monitor existente e o ActionFinance homolog. Se houver conflito de porta, escolher porta isolada e ajustar os endereços locais necessários; não parar processos alheios nem usar kill por correspondência ampla.

Validar os destinos de banco antes de iniciar: nenhum serviço deve acessar banco de produção. Usar credenciais locais próprias, ambiente explicitamente de teste e dados sem informações pessoais reais. Não chamar o processador para criar cobranças. Não habilitar simulador para substituir a listagem.

Se houver impedimento real de rede, pacote, credencial ou dependência, registrar a operação tentada, erro concreto, mitigação segura tentada e insumo indispensável. Concluir as outras atividades independentes. “Serviço não estava no ar” não é resultado final desta continuidade.

## 2. Executar a sincronização real

Popular o banco descartável do Hub com cobranças conhecidas, identificadas como teste: mais de uma página, datas iguais com IDs diferentes, valores válidos e ausentes, pendentes, aprovados e reembolsados. Incluir outra empresa para provar isolamento.

Acionar pela UI do AF. Demonstrar primeira carga, repetição sem duplicação e alteração de registro antigo na origem. Conferir valores contra os dados do Hub; distinguir valor cobrado de valor pago caso ambos existam. Ausência não vira zero.

Verificar paginação sob alteração concorrente: limite da janela, empate de timestamps, atualização de item já percorrido e registro alterado durante a leitura. A afirmação de que o registro aparecerá na próxima janela precisa ser comprovada, inclusive no limite do checkpoint. Corrigir se houver perda ou janela que nunca termine. Manter contrato documentado.

Interromper entre páginas e reiniciar o AF. Provar retomada a partir de checkpoint confirmado e ausência de RUNNING órfão bloqueando indefinidamente novas sincronizações. Não resolver o teste limpando registros manualmente. Provar também dois acionamentos concorrentes e acesso negado ao viewer/empresa indevida.

## 3. Tornar o percurso visível

Em navegador real, executar 360, 768 e 1280 px. No AF, clicar “Sincronizar recebimentos” e “Ver execução na Spider”. O Monitor deve abrir a execução correta e apresentar os fatos instrumentados: solicitação, autorização da empresa, seleção da capacidade, chamada do provider, resposta e devolução.

Registrar execução raiz e correlações de páginas/tentativas em AF, Spider e Hub, sem segredos. Não substituir eventos reais por etapas desenhadas. Validar que o link funciona e que o Monitor aplica o controle de acesso previsto.

Capturar as duas telas, com viewport e fullPage normalizado no topo, sem overflow. Mostrar na evidência o provider real local e a classificação de teste. O guia deve conter URLs verificadas e passos realmente executados, não apenas o percurso esperado.

## 4. Interrupção da Spider

Com o Hub e provider saudáveis, registrar o contador de chamadas e interromper somente a Spider isolada. Acionar no AF: contador não aumenta, registros importados permanecem e a interface informa indisponibilidade. Religar e retomar pelo mesmo percurso. A prova precisa incluir a engine e o Monitor, não apenas o mock dos ITs.

## 5. Integridade e restauração local

Comparar títulos, baixas e movimentos antes/depois: sincronização não cria fatos financeiros internos. Fazer backup/restore das estruturas V12 em outro banco descartável, conferir migrations, permissões, transações importadas, revisões e checkpoints. Nenhum RDS ou recurso AWS faz parte desta prova. A pendência de sessões do PRM_007 não entra aqui.

## 6. Entrega

Salvar este documento integral em documents/prompts/ACTIONFINANCE_PRM_009_CONTINUIDADE_001.md. Acrescentar ao REV_009 as provas da execução, estado final dos serviços e eventuais correções, preservando o relatório inicial. Atualizar o guia e índice.

Guardar logs e capturas em diretório próprio desta execução. Reexecutar testes dos componentes alterados; rodar verify AF se backend/migrations mudarem. Não repetir indiscriminadamente suites de componentes inalterados. Separar evidência de teste unitário, IT e percurso real.

Concluir com demonstração pronta para o proprietário: endereços locais verificados do Finance e Monitor, empresa de teste, ação a clicar e execução a localizar. Não imprimir tokens ou senhas. Manter serviços locais necessários disponíveis, respeitando o gerenciamento existente.

Sem produção, deploy, commit/push, dinheiro real, payout, baixa automática, Panne ou PRM_010. Código real do Hub com banco de teste continua diferente de sandbox do processador e de dados reais da loja. Parar para o aceite após a demonstração e as provas, ou apresentar dependência externa concreta que realmente impeça concluí-las.
