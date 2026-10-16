# ACTIONFINANCE — Prova da jornada financeira — 053

Data: 16/10/2026. Candidata 0.2.10 sobre a 0.2.9 publicada. Aceite não atribuído. Prova isolada, não autenticada em produção. Nenhuma carga produtiva.

## Base testada

A publicação conferida antes desta rodada continua a 0.2.9, task `actionfinance-web:26`, bundle `index-Ywb7z5Cf.js`, schema V24, imagem linux/amd64 `sha256:52a5ac3e5617465b791fcaf03b68e7c81cdd21fcb11bff7dfbdd70312c0e1b94`.

O laboratório usou o código dessa base mais a correção que faltava para o clique: a tela de conciliação só classificava uma iniciativa e pedia o valor da referência em centavos. Não havia como aplicar a regra de rateio, conciliar o livro nem desfazer. A API já fazia isso. A correção ficou na própria tela, em reais, e o detalhe passou a devolver o histórico da classificação. Não houve migration. A agenda, os cálculos e a navegação global não foram refeitos.

O banco foi um Postgres novo, container `af-jornada-053`, porta 5442, inicializado com `test-init.sql`. Não é o banco produtivo nem o da porta 5439. O backend local-demo apontou só para essa porta. O Vite em `http://127.0.0.1:5179/` foi o navegador da prova.

As capturas descritas no relato 052 não estavam em `documents/reviews/evidence` nem em `documents/reviews/screenshots`. A pasta temporária daquela rodada também não as conservava. Este relato não as recria para mudar de diretório. O adendo do 052 registra que o “zoom CSS” não é zoom de navegador.

## Preparação sintética

Pela API local, com o token de demonstração da empresa Padaria Exemplo:

- vínculo da conta banco com `mp-conta-cls-049` e da conta caixa com `usr-sanitizado-032`;
- confirmação do arquivo de oito eventos, separado, com o rateio de R$ 10,01;
- confirmação de `settlement-v2-sanitizado-022.csv`: 22 preservadas, 4 no total, 18 em revisão;
- confirmação de três linhas de livro, também separadas: líquido R$ 85,00, R$ 20,00 e R$ 30,00;
- títulos e baixas de ensaio. A referência comercial de R$ 90,00 ficou em aberto. As baixas de R$ 90,00, R$ 5,00, R$ 20,00 e R$ 30,00 foram registradas pela API de baixa, não por insert de decisão.

Nenhuma classificação, rateio, referência ou conciliação foi gravada direto no banco.

## O que a interface fez

Edge, 1440 px, empresa Padaria Exemplo.

1. A agenda de outubro mostrou o dia 20 com “Ensaio agenda receber” R$ 80,00 e “Ensaio agenda pagar” R$ 30,00. O título abriu e o Voltar voltou a `vista=calendario&mes=2026-10&dia=2026-10-20`.
2. O lote `d533a690-1ad1-405e-a425-da2641cd00e1` mostrou 22 preservadas, 4 no total e 18 em revisão. O filtro de revisão manteve as 18 fora do total.
3. “Pagina tres” foi classificada em Vendas. Em seguida, “Pagina um” e “Pagina dois” na mesma seleção. O histórico ficou “Versão 1. Classificação confirmada pelo operador.” O bruto do rateio continuou 1001 centavos e a descrição “Rateio de ensaio”.
4. Foram criadas as iniciativas Ensaio Alfa e Ensaio Beta e a regra “Meio a meio ensaio”, 50% e 50%, vigente em 01/10/2026. Aplicada ao evento de R$ 10,01, a tela mostrou Ensaio Alfa R$ 5,01 e Ensaio Beta R$ 5,00, com a regra do resíduo. A leitura posterior da API repetiu 501 e 500.
5. A referência da linha de R$ 85,00 foi confirmada para “Venda comercial de ensaio”, base bruto, R$ 90,00. O título seguiu OPEN e o restante R$ 90,00. A cobertura do livro não somou esses R$ 90,00: depois do grupo, “No livro” ficou R$ 85,00.
6. A linha de R$ 30,00 recebeu R$ 10,00 de um recebimento de R$ 30,00. A tela mostrou conferido R$ 10,00 e diferença R$ 20,00. O grupo da linha de R$ 85,00 reuniu entrada R$ 90,00 e saída R$ 5,00. A diferença ficou R$ 0,00. A lista, recarregada, marcou essa data como “Conciliado com o livro”. Nada foi criado para cobrir diferença.
7. A conciliação parcial foi desfeita com motivo. A API ficou com status UNDONE.
8. A linha de R$ 20,00 foi conciliada e, em seguida, a baixa foi estornada pela tela do registro. O restante do título voltou a R$ 20,00, situação sem baixa. A conciliação dessa linha passou a INVALID, com o histórico “A baixa associada foi estornada. A conciliação deixou de valer.” O texto da tela diz que não é reembolso nem cancelamento no Mercado Pago. A agenda de 04/10/2026 mostrou de novo “Credito exato de ensaio”.

As linhas do perfil de 22 ocorrências chegam sem descrição. A tela diz “Sem descrição” e o líquido distingue o evento. Não foi preciso digitar identificador.

## Contagens no laboratório, ao final

Títulos 21, baixas 7, estornos 2, movimentos 12, decisões 4, alocações de livro 4. O estorno de ensaio é o registro novo em relação à preparação. Classificar, ratear, referenciar, conciliar e desfazer não criaram título, baixa nem movimento. As quatro alocações são o grupo de duas, a parcial desfeita e a de R$ 20,00 invalidada.

## Capturas

Diretório `documents/reviews/screenshots/prm-053/`. Largura no nome do arquivo. Nenhuma rolagem horizontal de página foi medida em 1440, 1280, 768 e 390.

- `1440-calendario-preenchido.png`, `1440-dia.png`, `1440-titulo.png`, `1440-retorno.png` — agenda, dia 20, título e retorno.
- `1440-extrato.png`, `1440-extrato-revisao.png` — lote com 4 no total e 18 em revisão.
- `1440-classificacao.png`, `1440-classificacao-lote.png` — uma classificação e a seleção.
- `1440-iniciativas.png`, `1440-rateio-regra.png`, `1440-rateio-aplicado.png` — cadastro, regra 50/50 e R$ 5,01 / R$ 5,00.
- `1440-referencia.png`, `1440-parcial.png`, `1440-grupo.png`, `1440-grupo-lista.png`, `1440-conciliado-linha.png` — referência, diferença de R$ 20,00, grupo e a linha conciliada.
- `1440-desfazer.png`, `1440-exato.png`, `1440-estorno.png`, `1440-livro-invalidado.png`, `1440-agenda-apos-estorno.png`, `1440-resumo.png`.
- `1280-calendario.png`, `768-calendario.png`, `390-calendario.png`, `1280-conciliacao.png`, `768-conciliacao.png`, `390-conciliacao.png`, `390-grupo.png`, `390-grupo-diferenca.png`, `390-grupo-rolagem.png`.

Em 390 px a grade da agenda permanece e a conciliação abre o movimento abaixo da fila. Na rolagem, a barra superior ficou no topo e a página não cresceu na horizontal.

## Zoom de navegador

Não concluído. No Edge dirigido pelo executor, headless e com janela, Control combinado com Equal, NumpadAdd e + deixou a largura em 1440, a fonte do título em 28 px e `visualViewport.scale` em 1. Não houve reflow. Ampliação CSS não foi usada no lugar. Esta prova de 200% permanece aberta.

## Alcance

Isto não é aceite do proprietário nem prova com sessão de produção. Spider, Hub, Mercado Pago e Cognito não foram alterados. O laboratório foi encerrado de propósito ao fim da coleta.
