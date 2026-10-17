# ISA — planejamento para decidir antes da falta

Data: 16/10/2026. Protótipo **0.5.0**. Baseline proposta **1.2**. Não publicada, não aceita e sem operação bancária.

Os Prompts 001, 002, o Adendo 002A e o Prompt 003 permanecem. Este documento diz o que o planejamento guarda, como calcula e o que ainda falta para uma pessoa real entrar.

## Objetivo

A ISA ajuda quem está começando a ver se o dinheiro disponível cobre os compromissos do mês. A primeira decisão demonstrável é esta: há uma insuficiência antes da próxima renda, e uma mudança explícita de data altera o ponto mais baixo sem apagar o compromisso.

Importar, registrar e categorizar continuam sendo meios. Categorizar não é obrigatório para lançar nem para simular.

## Jornada

As cores claras, os acentos pastel, o texto escuro e os botões grandes permanecem. O menu tem quatro passos: Início, Lançamentos, Planejar e Perfil.

O Início abre no próximo problema. Se faltar a base, o botão pergunta quanto há disponível e em qual data. Com a base completa, mostra a próxima entrada confirmada, os compromissos próximos, o menor disponível e a primeira data em que o saldo fica negativo ou invade a reserva protegida.

Planejar faz três perguntas, uma de cada vez:

1. Quanto você tem disponível e em qual data?
2. Quando espera receber novamente e quanto?
3. O que precisa pagar até lá? Em cada compromisso: o que é, quanto e quando vence.

Recorrência, prioridade e condições ficam fora do primeiro formulário. **Ainda não sei** deixa o campo pendente. Campo vazio não vira zero.

**Posso gastar?** pede valor, categoria opcional e data. A resposta diz qual dia limita a margem. Sem orçamento declarado, não inventa verba mensal da categoria.

A comparação mostra o plano atual e uma alternativa de data. O texto inclui **Custo do adiamento ainda não informado** quando não há fonte de custo. Guardar usa o rótulo **Plano escolhido**. O vencimento original do compromisso permanece.

## Conceitos gravados

Cada linha tem dono e origem. Não viram um único tipo de lançamento.

| Conceito | O que guarda |
| --- | --- |
| Observação de saldo | Valor, moeda implícita BRL, data, tipo e fonte. Um saldo contábil antigo não entra como disponível. |
| Disponibilidade | Valor declarado para uma data, parcela protegida e convenção de encerramento do dia. Corrigir substitui a linha ativa e recalcula. |
| Entrada prevista | Valor, data, recorrência quando houver, origem e estado (`confirmada` ou `incerta`). Incerta fica fora da trajetória principal. |
| Compromisso | Total, restante, vencimento, vencimento original, essencial declarado, prioridade, recorrência e condições conhecidas. |
| Reserva | Valor conhecido, valor utilizável, data e se já está dentro da base. Sem o necessário para usar, não entra como fonte. Limite de crédito não soma. |
| Cenário | Premissas, horizonte, alteração proposta, resultado do motor e versão do cálculo. Não reescreve o compromisso. |
| Sugestão | Conteúdo apresentado, premissas fotografadas, resultado do motor, origem e eventos de vida. |
| Rascunho | Trabalho ainda aberto, como uma conferência, para continuar depois de sair. |

A edição de uma ocorrência de série altera só aquela linha.

## Motor

O cálculo mora em `server/engine.py`, versão `isa-projecao-1`. O navegador não recalcula a trajetória. Centavos inteiros e datas civis `AAAA-MM-DD`. A data de referência dos testes é 16/10/2026 e o horizonte inicial vai até 30/11/2026, estendido se um evento cair depois.

A trajetória parte da disponibilidade na data conhecida. Movimento já refletido nessa base, em especial no próprio dia quando a convenção é encerramento do dia, não entra de novo. Reserva protegida é piso de comparação: não é despesa extra e não é somada outra vez. Reserva já contida na base não vira nova entrada. Transferência entre contas próprias não aumenta o consolidado.

No mesmo dia, sem horário, o saldo de fechamento soma entrada e saída. Se a ordem mudar a viabilidade diante do piso ou de zero, a dependência aparece no resultado. Saldo negativo permanece.

O restante de um compromisso parcialmente vinculado é o que segue na projeção. O vínculo pede confirmação e não desconta duas vezes o mesmo movimento. Sugestão de texto não quita compromisso.

A margem de um gasto adicional é o menor excedente sobre o piso protegido, da data do gasto até o fim do horizonte. Margem negativa deixa a capacidade adicional em zero e mostra o déficit à parte. Sem base, a projeção fica parcial e a pergunta que falta é a resposta, não um zero.

A margem global não é oferecida inteira para cada categoria. Sem orçamento declarado, o texto explica o efeito na trajetória.

## Cenário de referência

Valores fictícios, data 16/10/2026. Disponível R$ 600,00, com R$ 100,00 de reserva protegida dentro dessa base. Entrada confirmada de R$ 1.200,00 em 25/10. Compromissos de R$ 200,00 em 18/10, R$ 500,00 em 20/10 e R$ 300,00 em 28/10.

O disponível chega a −R$ 100,00 em 20/10 e outubro termina em R$ 800,00. Para também preservar a reserva, faltam R$ 200,00 no ponto mais baixo. A margem para gastar em 16/10 é zero.

Mover só o compromisso de R$ 500,00 para 26/10 leva o mínimo a R$ 400,00 e outubro continua em R$ 800,00. Um compromisso em novembro permanece no horizonte. Uma entrada incerta não entra na trajetória confirmada.

## Agente de planejamento

Contrato desta etapa: o agente recebe fatos permitidos, lacunas e o resultado do motor. Pode propor pergunta e explicar alternativa. Não produz número final fora do motor, não inventa fonte, não transforma previsão em confirmação, não altera obrigação e não executa pagamento.

Não há provedor autorizado. `server/explain.py` escreve os textos com a versão de regra `regras-demonstrativas-1` e a versão de prompt `isa-planejamento-004`. A origem gravada é `regras-demonstrativas`. Provedor e modelo ficam vazios. O texto diz que nenhum agente foi chamado.

A fronteira do agente de categorização do Prompt 003 permanece. A ausência dele não bloqueia importação nem planejamento. Correção humana não é substituída por resposta tardia: sugestão já recusada ou corrigida não volta ao estado anterior quando as premissas mudam; o que ainda estava só gerado ou apresentado é marcado como desatualizado.

Cada sugestão é gravada com estado `gerada` antes de poder ser decidida. `apresentada` é outro evento. Aceitar guarda um plano e não paga. Repetir o aceite devolve a mesma decisão. Falha de gravação não é tratada como sucesso na tela: o estado visível é **Não foi possível salvar**.

## Identidade

O diretório próprio da ISA não existe. A aplicação não guarda senha e não usa o pool empresarial.

No laboratório, `ISA_ENV=lab` aceita o cabeçalho `X-ISA-Lab-Person` com `marina` ou `paulo`, mapeados no servidor para `pessoa-marina` e `pessoa-paulo`. Identidade ausente ou desconhecida recebe 401. Qualquer outro `ISA_ENV`, inclusive produção, responde 403 e recusa o mecanismo. O corpo do pedido não escolhe `ownerId`.

Isso prova isolamento entre duas pessoas de teste. Não prova cadastro nem autenticação produtiva.

Decisão ainda necessária para acesso real: operar um diretório só da ISA, no qual o servidor derive o dono de uma identidade validada, sem senha na aplicação e sem o pool do Finance. Enquanto essa decisão não for tomada, a persistência local e a demonstração sintética seguem sem esse serviço.

## Persistência e recuperação

Tecnologia: Python da biblioteca padrão e SQLite, no mesmo processo que serve o protótipo em `127.0.0.1:8098`. A escolha evita um segundo banco e um segundo motor no navegador, e não abre o banco do Finance. O leitor do Banco do Brasil continua em `prototype/bb-statement.js`.

A migração `schema_migration` versão 1 cria disponibilidade, observação de saldo, entrada, compromisso, reserva, cenário, lote, ocorrência, movimento, vínculo, rascunho, sugestão, evento de sugestão, arquivo, histórico de alteração e chave de idempotência.

Arquivos de origem desta etapa só entram com rótulo que começa por `sintetico`, com identificador, SHA-256 e retenção `laboratorio-7-dias`. O CSV real da validação privada não é copiado para essa base.

Cópia: `POST /api/backup` grava banco e arquivos num destino que não pode ser a pasta ativa nem ficar dentro dela. O manifesto marca `sameDiskLimitation`. Uma cópia no mesmo disco não protege contra perda do equipamento. Antes de uso real, a cópia precisa ir para um armazenamento independente.

Restauração: `store.restore_dir` copia a base e os anexos para um diretório vazio. A prova automatizada faz isso num ambiente isolado e confere dono, quantidades, vínculo, fila, cenário, plano, sugestões nas duas versões, rascunho aberto e o SHA-256 do anexo.

Retenção de laboratório: 7 dias a partir da data do manifesto. `expire_backups` remove a pasta vencida. Esquecer os dados ativos apaga as linhas e os arquivos da pessoa e deixa a cópia já feita até o prazo. Restaurar essa cópia traria de volta o que foi esquecido, até a cópia expirar. Não há retenção eterna.

Perda máxima entre cópias: tudo o que mudou desde a última cópia manual. Esta etapa não agenda cópia automática.

A tela mostra **Salvando**, **Salvo neste computador.** ou **Não foi possível salvar**, conforme a resposta do servidor.

## Execução local

Na pasta `C:\Projetos\isa`:

```powershell
.\scripts\dev\start-isa.ps1
```

Abre `http://127.0.0.1:8098`. A identidade é sintética de laboratório. Entrar como Marina Alves ou Paulo Nunes não é login de produção. A base ativa fica em `data\lab`, ignorada pelo Git. As cópias ficam em `data\backups`.

O protótipo estático anterior, quando estiver no ar, continua em `http://127.0.0.1:8097` para a jornada de importação do 0.4.0. Nessa porta não há API; o bloco de planejamento fica vazio e a lista do mês segue como antes.
