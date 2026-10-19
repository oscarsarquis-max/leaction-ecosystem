# ISA 0.6.4 — Acabamento do Início

19/10/2026. Continuação da 0.6.3. O host público, antes desta entrega, respondia `isa-piloto 0.6.3` na task `isa-web:12`. O acabamento não altera cálculos, schema nem dados.

## O que mudou

A barra azul e o menu permanecem. O logo continua o arquivo opaco `prototype/logoisantrans.png`. No desktop a imagem passa de 150×44 px para 172×46 px, com enquadramento `object-position: center 48.4%`, dentro da mesma barra de 56 px. A ampliação vem da largura e do recorte mais próximo das letras, sem cortar o desenho. Em até 389 px a imagem fica em 156×42 px.

No Início vazio, os três cartões usam o mesmo desenho: título, estado sem o peso de um valor, uma linha de contexto e uma ação curta. Disponível pede “Informar valor”. A pagar diz “Nenhuma conta informada”, sem tratar isso como ausência de despesa e sem mostrar R$ 0,00. Próxima entrada pede “Informar entrada”. O período aparece uma vez, com a data real do cálculo. A explicação completa continua em “Como este valor é calculado”.

Com dados, o valor, a data e a contagem ficam em destaque. A cobertura da soma a pagar segue identificável como compromissos informados; o detalhe conserva o nome do motor, “Compromissos do planejamento”. A frase de situação incompleta aparece uma vez: “Informe seu disponível para calcular se o dinheiro chega.” O aviso de encargo calculável continua em reais, com multa, juros, total e data. Sem condições, a frase de encargo desconhecido aparece uma vez.

O calendário deixa de usar a classe `.mark` da marca. A legenda é Entradas, Saídas e Atenção, com símbolo e cor. Anterior e Próximo usam o botão secundário e não quebram o nome. Sem eventos, a frase é “Nenhum compromisso neste calendário.”, com acesso para informar contas.

A leitura de IA, quando há um aviso para interpretar e ainda não existe leitura válida do mesmo contexto, é pedida uma vez ao abrir o Início. A seleção de dia não pede de novo. Uma segunda abertura recebe o mesmo trabalho já enfileirado. Falha anterior não gera outro pedido até “Atualizar a leitura”. Sem aviso, o servidor responde que não há o que interpretar e não grava trabalho. A cota diária continua reservando espaço para um pedido manual. Abrir o Início não grava conta nem movimento.

## Medida da marca

Nas capturas de 1280 px, a caixa das letras brancas dentro da barra azul, separada do nome da conta:

| | Largura | Altura | Área |
|---|---:|---:|---:|
| 0.6.3 | 122 px | 17 px | 2.074 |
| 0.6.4 | 140 px | 20 px | 2.800 |

A área das letras cresceu cerca de 35%. A barra continua nas linhas 0 a 55. A legenda “ISA PERSONAL FINANCE” continua pequena: é o limite do arquivo raster reduzido, não um título.

## Verificação de laboratório

Base temporária, Paulo e Marina sintéticos. Não é a conta publicada.

Trinta testes de motor, visão e jornada passaram. A prova do Início percorreu o estado vazio, o retorno depois de informar 1.500,00, a falta com encargo de R$ 30,00 e total estimado de R$ 1.030,00, a conta suficiente de Marina e a largura de 360 px sem estouro da barra. A jornada de planejamento abriu o formulário do disponível, recusou campo vazio e seguiu em Salvar e continuar.

O zoom de 200% foi o do Chromium, pela preferência `partition.default_zoom_level`, com janela de 1280 px e densidade de tela forçada em 1 para não confundir com a escala do Windows. Em 100%, a largura útil foi 1280, a densidade 1, o menu superior visível e os três cartões lado a lado. Em 200%, a largura útil foi 640, a densidade 2, a navegação foi para a base e os cartões ficaram em uma coluna. Não houve rolagem horizontal. Não se usou viewport de 640 px nem zoom de CSS como prova.

Capturas anteriores em `documents/reviews/acabamento-004ia3r2/antes/`. Capturas desta versão em `depois/`, mais `antes-marca.png`, `depois-marca.png`, `zoom-100.png` e `zoom-200.png`. As capturas da 0.6.3 em `documents/reviews/inicio-004ia3/` foram preservadas.

## Publicação

A preencher depois da troca da imagem, com a versão servida, a task e o retorno.
