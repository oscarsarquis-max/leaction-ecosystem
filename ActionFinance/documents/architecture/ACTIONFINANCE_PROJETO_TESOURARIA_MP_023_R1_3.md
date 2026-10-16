# Projeto de tesouraria — AF-BL-023 revisão 1.3

Data: 16/10/2026. Esta revisão de requisitos não é versão de produto. As revisões 1.0, 1.1 e 1.2 permanecem. Aceite do proprietário não atribuído.

A 1.2 descrevia o extrato como ainda não persistido, a migration V21 como ainda não escrita e o extrato como item futuro sob Recebimentos. Isso foi superado pelas versões 0.2.0 a 0.2.6, schema V23 e pela navegação deste incremento. As decisões financeiras que continuam válidas estão repetidas aqui com a fonte.

## 1. Como ler o estado

| Marca | Significado |
|---|---|
| Publicada | Está na imagem servida e no código identificado |
| Laboratório | Provada com dado sintético ou de demonstração, não na conta do proprietário |
| Uso real | Operação comprovada na empresa do proprietário, com sessão |
| Pendência | Limite conhecido, sem número histórico tratado como estado atual |
| Planejada | Requisito da próxima entrega. Não está no menu |

## 2. O que está publicado

Origem: relatos 034 a 047 e a verificação do host em 16/10/2026, produto 0.2.6 antes deste incremento de navegação.

| Capacidade | Marca | Fonte |
|---|---|---|
| Leitura manual de arquivo antes do vínculo | Publicada | 0.2.3, REV_043 |
| Confirmação de identidade da conta, sem trocar vínculo divergente | Publicada | 0.2.3 |
| Prévia, seleção e confirmação idempotente do lote | Publicada | 0.2.0–0.2.5 |
| Ocorrências preservadas, inclusive ambíguas, fora do total elegível | Publicada | 0.2.2–0.2.5 |
| Consolidação só do que é elegível e liberado para o efeito | Publicada | 0.2.2, 0.2.5 |
| Apresentação da prévia e do extrato no padrão aprovado | Publicada | 0.2.4 e 0.2.5, prévia 045 |
| Contas: lista, cadastro, detalhe, posição e movimentos do livro | Publicada | 0.2.6, REV_047 |
| Saldo desconhecido distinto de zero informado | Publicada | 0.2.3 e 0.2.6 |
| Observação de cobrança ActionHub Pay, sem virar extrato nem baixa | Publicada | 0.1.1–0.1.2, mantida |

## 3. Limites que continuam

| Limite | Marca | O que não se conclui daí |
|---|---|---|
| Importação do relatório real na conta do proprietário | Pendência | O último relato não comprova essa carga. Laboratório usou arquivo sanitizado |
| Nove pares ambíguos | Pendência | Ficam preservados e fora do total. Não se inventa estorno, parcela ou compensação |
| Soma parcial do extrato | Laboratório | Não é posição de caixa. Falta saldo inicial comprovado da conta real |
| Segunda confirmação com 409 | Publicada como outra operação | Não demonstra reenvio idempotente do arquivo. Confirmar de novo e reenviar o arquivo são atos diferentes |
| Sugestão de vínculo | Publicada como sugestão | Não é conciliação concluída |
| Classificação, rateio, conciliação confirmada, posição consolidada e projeção | Planejada | Não entram no menu até a jornada funcionar |
| Detalhe autenticado do pagamento citado no 027 e repetição sem gravação nova | Pendência | Continuam sem prova de sessão do operador |

Números antigos de registros de produção não são o estado atual.

## 4. Fatos que não se somam

Mantidos da 1.2, seções 4 e 5, porque continuam válidos:

Observação de cobrança, ocorrência de arquivo, evento de extrato, obrigação, baixa e movimento gerencial são fatos distintos. Não são fontes independentes do mesmo dinheiro. Sugestão não grava vínculo. Confirmar importação não cria título, não baixa e não movimenta caixa. Transferência entre contas próprias não é receita. Estorno preserva a linha original. Moeda ausente fica fora da soma. Coluna ausente não vira zero.

A empresa não é iniciativa. O código de aplicação, inclusive o da Loja de Pães, pode sugerir uma iniciativa no futuro; a sugestão não confirma e nenhuma migração transforma a empresa em iniciativa. O seletor de empresa continua sendo a empresa titular.

## 5. Navegação

O mapa de destino, aprovado em 16/10/2026, é: Visão geral; Tesouraria (contas, extratos, conciliação, fluxo); Recebimentos; Pagamentos; Análise e planejamento; Cadastros.

O menu servido só mostra o que funciona e o usuário pode acessar. Neste incremento: Tesouraria (Contas e Extratos), Recebimentos (A receber e Recebimentos integrados), Pagamentos (A pagar) e Cadastros (Clientes e fornecedores, Categorias). Visão geral, Análise e planejamento, Conciliação, Fluxo de caixa, Iniciativas e Rateios não têm página vazia.

As URLs existentes permanecem. A administração de categorias fica em Cadastros. A análise por categoria fica em Análise e planejamento, quando essa área existir.

## 6. Próxima entrega — classificação e conciliação

Resultado para o usuário: classificar uma linha ou um lote, atribuir iniciativa, aplicar uma regra de rateio com vigência e ver a cobertura. Confirmar ou desfazer um vínculo explicável. Despesa compartilhada permanece «Não atribuída» até haver regra ou decisão.

Fonte: classificações já gravadas e a decisão do operador. Linha de extrato e título não se somam. A sugestão mostra a evidência; igualdade de data e valor não confirma.

Dependências: extrato confirmado e cadastro de categoria já publicados. Iniciativa e regra de rateio nascem nesta entrega, com histórico. Sem schema só para menu.

Fórmula: o valor classificado de uma linha é a soma das partes atribuídas. Cada ponta de um vínculo parcial ou agrupado declara seu limite. A parte sem regra fica não atribuída, não rateio igual invisível.

Exceção: linha ambígua continua fora do total elegível e pode ser classificada só como ocorrência preservada, sem entrar no dinheiro elegível. Moeda ausente não recebe categoria que a faça entrar na soma.

Recuperação: desfazer volta ao estado anterior da decisão, sem apagar a ocorrência. Resposta incerta de gravação repete a mesma chave.

Conclusão: o operador explica, sem código, o que foi atribuído, o que ficou de fora e por quê. A interface, os filtros e a cobertura acompanham esta entrega. Não há fase separada só de acabamento visual.

## 7. Entrega seguinte — posição e compromissos

Resultado: saldo informado com data e origem; saldo gerencial só com base comprovada; diferença de conferência; agenda dos títulos ligados à conta.

Fonte: saldo inicial registrado, movimentos do livro e títulos com vínculo real à conta. Título da empresa inteira não entra na agenda da conta.

Fórmula: posição gerencial = saldo inicial datado + movimentos válidos desde essa data. Diferença de conferência = posição informada pela fonte, na data dela, menos a posição gerencial na mesma data. Sem saldo inicial, a posição calculada não é exibida como conhecida. A agenda e o fluxo de compromissos continuam consultáveis.

Exceção: zero informado permanece zero. Desconhecido não vira zero. Importação não vira saldo inicial.

Recuperação: corrigir um saldo informado gera outro registro datado; não reescreve o anterior em silêncio.

Conclusão: o operador distingue saldo anterior, final do período e atual, cada um com data e origem, e sabe se a conferência está incompleta.

## 8. Entrega seguinte — fluxo e planejamento

Resultado: realizado, projeção até 13 semanas, menor saldo projetado e cenários nomeados. Cortes por categoria e iniciativa quando a classificação existir.

Fonte: realizado vem do livro ou do extrato elegível, declarados e não somados entre si. Previsto vem de títulos em aberto e de hipóteses do cenário. A Visão geral só consolida o que já estiver utilizável.

Fórmula: projetado = base declarada + compromissos futuros do cenário. Realizado e previsto do mesmo fato não entram os dois. Sem base confiável, mostram-se os compromissos e as hipóteses, não um saldo projetado.

Exceção: cenário sem nome não aparece como previsão. Linha ambígua não entra no realizado.

Recuperação: trocar de cenário não grava o anterior por cima. A hipótese fica visível.

Conclusão: o operador vê o menor saldo do cenário e de qual hipótese ele depende.

## 9. O que esta revisão não autoriza

Cliente direto ao Mercado Pago. Mudança na Spider, no Hub ou no Cognito. Execução de pagamento, transferência ou estorno. Importação real em nome do proprietário. ISA. Tratar a Loja de Pães como iniciativa por migração. Anunciar classificação, conciliação, posição consolidada ou projeção como se esta entrega as tivesse feito.
