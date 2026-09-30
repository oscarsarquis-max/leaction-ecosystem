# ACTIONFINANCE_PRM_004_COR_001 — Correções de contas, baixas e extrato

Versão 0.1 — 29/09/2026.

## Instrução ao Cursor

Execute este corretivo em **C:\Projetos\ActionFinance**, no mesmo recorte funcional do PRM_004. Este é o prompt de implementação das correções apontadas em ACTIONFINANCE_REV_004_PARECER_ANALISTA.md. O parecer é referência; este documento contém o trabalho a executar e os critérios de entrega.

Não iniciar PRM_005. Não reabrir fundação ou PRM_003, não redesenhar o domínio nem adicionar integrações. Preservar dados locais, volumes, versões aprovadas e migrations já aplicadas. Não alterar Spider, ActionHub, Panne, regras globais ou configurações globais da máquina. Sem commit, push, deploy ou autorização de produção/piloto.

ActionFinance continua produto autônomo e integrável. Esta fatia registra fatos financeiros locais; não executa dinheiro. As logos compactas aprovadas permanecem intactas, com dimensões, proporções e margens preservadas. Não incluir reformulação visual geral neste corretivo.

Leia as instruções locais aplicáveis, PRM_004, relatório REV_004 e parecer do analista. Inspecione o estado atual antes de editar e preserve alterações alheias. Se algum ponto já estiver corrigido, comprove-o e não reimplemente.

## C1 — Repetição segura nas escritas de conta

No código revisado, AccountCreateDialog cria uma nova Idempotency-Key em cada submissão. AccountDetailPage faz o mesmo nas alterações de nome/situação. Isso deixa as novas operações fora do mecanismo seguro já implementado no produto.

Use o mecanismo existente freezeWrite/sendPending e a classificação de resultado desconhecido em:

- criação de conta no diálogo aberto a partir da baixa;
- criação pela página dedicada, verificando sua implementação existente;
- renomear, inativar e reativar conta.

Preservar chave, rota, corpo, empresa e ator enquanto o resultado for desconhecido. Bloquear duplo envio concorrente. Falha de transporte ou perda de resposta não autoriza criar uma nova operação automaticamente. Mostrar mensagem clara e ação para repetir o pedido pendente. Erro definitivo de validação permite corrigir os campos e iniciar nova operação. Troca de contexto não reenvia pedido anterior.

Não resolver apenas escondendo o botão ou gerando nova chave a cada clique. A autorização e idempotência no servidor continuam obrigatórias.

**Prova:** simular sucesso de criação seguido de perda de resposta, repetir pelo diálogo e verificar a mesma chave/corpo. Comprovar pelo teste de integração correspondente que há uma única conta e um único movimento OPENING. Distinguir a simulação de transporte no frontend da prova de persistência no banco. Cobrir também atualização de conta e correção após erro definitivo.

## C2 — Recuperação de conflito e de tentativa pendente na baixa

SettlementFormPage informa VERSION_CONFLICT, mas a implementação revisada mantém title.version antigo. Além disso, no botão Tentar novamente, uma resposta definitiva pode limpar pending.current e manter unknownResult ativo, deixando o formulário bloqueado sem operação a repetir.

Corrigir a máquina de estados da interface:

1. Em conflito, buscar versão e restante atuais do título.
2. Preservar os campos digitados; mostrar o restante atualizado e pedir que o usuário revise o valor.
3. Não reduzir automaticamente o valor nem reenviar silenciosamente.
4. Após revisão explícita, enviar novo pedido com versão atual e nova chave.
5. Se uma repetição de resultado desconhecido terminar em erro definitivo, limpar o estado pendente e devolver controles utilizáveis.
6. Enquanto o resultado continuar desconhecido, preservar o pedido original e oferecer repetição segura.

Aplicar comportamento equivalente ao estorno quando ocorrer conflito de versão. Mensagens em português, sem exigir atualização manual da página. Manter saída protegida e prevenção de reenvio em empresa/usuário diferente.

**Provas:** duas sessões disputam o restante de um título; a segunda recebe conflito, revisa e conclui sem reiniciar a aplicação. Timeout seguido de 400/409 na repetição deixa a tela editável e recuperável. Cobrir as duas direções e a recuperação do estorno.

## C3 — Extrato com saldos e movimentos consistentes

AccountService.movements e JdbcAccountRepository.listMovements, na versão revisada, consultam conta, contagem, saldo anterior, soma do período, saldo atual e linhas em consultas separadas, sem uma fotografia transacional consistente.

Garantir a mesma fotografia para toda a resposta, usando transação de leitura com isolamento adequado ou solução equivalente. Preservar:

- saldo acumulado calculado antes da paginação;
- abertura primeiro no respectivo dia, seguida da ordenação definida no PRM_004;
- período inclusivo e distinção entre saldo anterior, final do período e atual;
- valores exatos em centavos, sem ponto flutuante;
- isolamento por tenant/empresa/conta;
- movimentos originais e inversos visíveis, sem apagar o histórico.

No frontend, o mesmo saldo atual exibido no cabeçalho e no extrato deve vir da resposta consistente, sem duas fontes concorrentes que apresentem números diferentes. Ao trocar rapidamente o período, ignorar respostas antigas. Durante carregamento/falha, não apresentar valores anteriores como se pertencessem ao novo filtro.

**Prova:** introduzir baixa/estorno concorrente durante a consulta e confirmar que saldo anterior + entradas − saídas = saldo final do período, com linhas e acumulados coerentes. Testar conjunto maior que uma página e movimento retroativo. Aproveitar testes existentes, sem duplicá-los apenas para aumentar contagem.

## C4 — Valores do extrato mobile sem ambiguidade

Os cartões revisados mostram somente balanceAfterMinor em destaque. Isso faz, por exemplo, um recebimento de R$ 50,00 aparecer acompanhado de R$ 300,00 sem explicar que 300 é o saldo posterior.

Cada cartão deve apresentar:

- data efetiva e tipo de registro;
- descrição e referência acessível;
- **Entrada: R$ 50,00** ou **Saída: R$ 100,00**, conforme o movimento;
- **Saldo após: R$ 300,00**, separado e rotulado;
- acesso ao detalhe da baixa para consultar referência, autor e instante, quando houver baixa associada.

A abertura recebe rótulo próprio, inclusive quando negativa ou zero. Estorno deve ser identificado como estorno do registro e mostrar sua entrada/saída efetiva. Não depender só de cor ou sinal. Não transformar o saldo posterior no valor principal sem rótulo. Manter 360 px sem overflow horizontal e alvos acessíveis; não refazer o layout inteiro.

**Prova visual:** capturas mobile de entrada, saída e estorno, com valores diferentes do saldo posterior. Validar também desktop para evitar regressão da tabela. Não alterar os arquivos de logo ou sua apresentação aprovada.

## C5 — Jornada real de navegador e provas de integridade

O relatório anterior declarou que a jornada de escrita no navegador não foi executada. Concluir essa prova com dados fictícios próprios, sem usar apenas o seed como evidência de funcionamento:

1. Criar conta com saldo inicial explícito.
2. Criar/usar título demonstrativo de R$ 150,00.
3. Registrar baixa de R$ 50,00 e conferir restante R$ 100,00.
4. Registrar R$ 100,00 e conferir quitação.
5. Estornar o registro de R$ 50,00 e conferir restante R$ 50,00.
6. Conferir baixas, histórico e extrato, incluindo valores de movimentos e saldos.
7. Percorrer recebimento e pagamento; verificar perfil de consulta sem escrita.

Guardar evidências de navegador em 1280/360 px e identificar exatamente o que foi clicado, automatizado ou simulado. Não afirmar prova de banco com base apenas em mock frontend.

Completar, se ausentes, os testes de rollback dos novos fatos e estorno concorrente previstos no PRM_004. Uma falha entre baixa/alocação/movimento/histórico deve reverter a transação; estornos concorrentes devem produzir um único movimento inverso. Não exigir novos módulos para provar essas invariantes.

Se a ferramenta de navegador estiver indisponível, registrar a limitação objetivamente; não declarar a jornada concluída com base em screenshots de seed.

## Gates e evidências

Rodar Maven verify completo com testes de integração, sem skips/falhas/erros; frontend lint, testes, build e audit completo. Repetir npm ci somente se dependências/lockfile mudarem ou houver motivo concreto. Não atualizar bibliotecas ou versões como trabalho paralelo.

Preservar as evidências válidas de backup/restore. Repetir restore se houver mudança em schema, grants ou persistência que afete suas garantias; não repetir por simples alteração de layout. Nunca apagar dados/volumes para fazer teste passar. Migrations aplicadas são imutáveis; eventual ajuste de schema exige nova migration justificada.

Agrupar logs e resultados por execução final em documents/reviews/evidence/prm-004-cor-001/. Capturas em documents/reviews/screenshots/prm-004-cor-001/. Distinguir diagnóstico intermediário do gate final e registrar quantidades reais de testes.

## Entrega e parada

Salvar este prompt integral em documents/prompts/ACTIONFINANCE_PRM_004_COR_001.md. Produzir documents/reviews/ACTIONFINANCE_REV_004_COR_001.md e atualizar índice/relatório PRM_004 com vínculo ao corretivo, sem apagar o parecer anterior.

Relatório de retorno:

| Campo obrigatório | Conteúdo |
| --- | --- |
| C1–C5 | Mudança, prova, resultado e eventual pendência |
| Jornada | Passos realmente executados no navegador e caminhos das capturas |
| Testes | Comandos, contagens, skips e exit codes |
| Dados | Confirmação de preservação; migrations novas somente se necessárias |
| Serviços | Estado final de UI/API/banco e dados de demonstração criados |
| Limites | Registro local; nenhuma operação externa de dinheiro |

Parar após a entrega. Não emitir nem executar PRM_005. O aceite pertence ao analista após o retorno do proprietário; não confundir execução com aprovação.
