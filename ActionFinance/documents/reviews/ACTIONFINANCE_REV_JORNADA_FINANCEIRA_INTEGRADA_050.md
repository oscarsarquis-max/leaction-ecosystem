# Jornada financeira integrada — Prompt 050

Data: 16/10/2026. Publicado junto com o 049 na candidata 0.2.8. Aceite não atribuído. Artefato e recuperação estão em [REV_051](ACTIONFINANCE_REV_FECHAMENTO_049_050_051.md).

## Navegação

Tesouraria abre em Resumo. Os itens são Resumo, Contas, Extratos, Conciliação e Agenda. O login continua em Recebimentos. Não há item vazio de fluxo, visão geral ou análise.

## De onde vem cada número

| Cartão | Fonte | Recorte |
|---|---|---|
| Em aberto e vencidos | Saldo residual dos títulos válidos em aberto | Situação atual. Vencido já está dentro do em aberto. Rascunho é só quantidade |
| Recebido e pago | Baixas válidas | Período explícito, data efetiva. Não é confirmação da origem |
| Parcial e diferença | Mesma situação da fila de conciliação | Eventos elegíveis do extrato ativo |
| Ocorrências em revisão | Linhas preservadas de lotes confirmados | Não são eventos únicos. Lote retirado fica no histórico |
| Posição | Movimentos do livro até a data, com saldo inicial já aplicável | Só contas ativas em real. Não é o total da empresa |

A agenda da empresa usa vencidos, hoje, os próximos sete dias, do oitavo ao trigésimo e sem data, sem sobrepor os intervalos. O compromisso em aberto diz que a conta ainda não está definida.

## Telas do recorte

| Tela | Antes | Agora |
|---|---|---|
| Lista a receber e a pagar | Lista com o invólucro novo | Cabeçalho, recorte e a legenda de que recebido ou pago é registro no Finance |
| Formulário do título | Fieldsets longos | Campos principais à esquerda e resumo do que será registrado à direita. Rascunho não entra na agenda |
| Detalhe do título | Referência no título da página | Valor em aberto, vencimento, equação original menos baixas válidas, volta ao retorno interno |
| Registrar baixa | Formulário único | Conta, data, valor, restante e efeito antes de confirmar. O texto não fala em pagar agora |
| Detalhe e estorno da baixa | Fatos em lista | Valor em destaque e efeito no título e no livro. Estorno não é reembolso |
| Recebimentos integrados | Lista e detalhe anteriores | Composição com a cobertura da integração separada do total armazenado |
| Resumo e agenda | Não existiam | Cartões com destino filtrado e agenda com faixa, direção e página na URL |

A comparação visual em 1440 e 390 px, e a checagem de 1280, 768 e zoom, não foram feitas no navegador. O que está publicado é o código provado no laboratório e nos testes de apresentação.
