# Comparação — fila de pedidos

A prancha aprovada (“Pedidos” e “Pedidos no celular”) não está no repositório. A comparação é com o layout escrito no prompt 109, usando `pedidos-1440.png` e `pedidos-390.png`.

## pedidos-1440.png

| Peça | O que a captura mostra | Leitura |
|---|---|---|
| Título e descrição | “Pedidos” em DM Sans e a frase das quatro trilhas, com “Atualizar” à direita | Conforme |
| Lente padrão | Vigentes pressionada | Intencional: a fila vigente continua sendo a vista inicial |
| Lentes | As nove pílulas, com contagem | Conforme. Em 1440 elas passam para uma segunda linha porque os rótulos não cabem numa só |
| Filtros | Buscar, Situação, Recebimento, Criado de, até e Filtrar na mesma linha | Conforme. Fornada ficou de fora: não há endpoint que liste fornadas |
| Tabela | Referência, fornada, cliente, total, quatro selos e o próximo passo | Conforme |
| Próximo passo | Botão, sem executar a ação | Conforme |
| Frase “Fila operacional: só vigentes.” | Aparece sob os filtros | Intencional: é o recado de escopo que a lista já devolvia |

## pedidos-390.png

| Peça | O que a captura mostra | Leitura |
|---|---|---|
| Lentes | Faixa horizontal; “Abertos” aparece cortado na borda e segue na rolagem | Intencional: abaixo de 960 px a faixa rola (`data-scroll-x`) |
| Filtros | Botão “Filtros”, formulário recolhido | Conforme |
| Cartão | Referência, selo, nome, fornada · resumo · total, quatro trilhas, atenção e o botão em largura total | Conforme |
| Barra inferior | Não há | Intencional: fica para o 111 |
| Agenda e Ciclo | Não estão nesta rota | Conforme: `/admin/pedidos` é só a fila. Em `/admin` os dois blocos antigos continuam em cima, para o 111 |
