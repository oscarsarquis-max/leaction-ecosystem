# ISA — projeto do MVP

Baseline 1.0. Protótipo visual 0.1.0, em 16/10/2026. Proposta para aprovação. Não é produção e não está aprovada.

A tesouraria empresarial (ActionFinance) não faz parte deste recorte. Nenhum arquivo, banco, migração, autenticação, deploy ou tela dessa frente foi alterado para acomodar a ISA.

## O que este MVP é

A ISA é um módulo de finanças pessoais, com acesso direto e conta individual. Cada pessoa vê só os próprios lançamentos, comprovantes e sugestões. Não há conta compartilhada nem gestão familiar.

O primeiro uso cabe no celular, como site. Não há aplicativo para instalar nesta etapa.

A pessoa registra ganho ou gasto digitando, ou a partir de uma foto ou imagem de comprovante. A leitura automática, quando existir, só sugere. A gravação acontece no confirmar.

## O que fica de fora

- Saldo inicial, conta bancária e saldo disponível. O número do mês é o resultado do período: ganhos recebidos menos gastos pagos.
- Conciliação bancária, plano de contas e rateio por item do cupom.
- Treinamento de modelo por pessoa e uso do dado de uma pessoa para sugerir algo privado a outra.
- Cobrança, domínio, pool de identidade, serviço de IA contratado e qualquer comprovante real enviado a terceiro.
- Ligação automática entre a pessoa e a empresa ativa do Finance.

## Modelo individual

Cada registro carrega o proprietário. A consulta e a imagem também. A interface não é a barreira: o servidor recusa o que não for daquela pessoa.

| Registro | Campos mínimos |
| --- | --- |
| Pessoa | identificador próprio, separado do usuário empresarial |
| Lançamento | dono, direção (ganho ou gasto), natureza, descrição, valor em centavos, moeda, categoria, situação, data da nota, data da situação, data prevista, comprovante |
| Comprovante | dono, lançamento, tipo, tamanho, conteúdo privado, identificador do documento quando a leitura achar um |
| Sugestão | dono, campos propostos, origem da leitura, confirmação ou descarte |
| Preferência | dono, correção repetida, explicação, como desfazer |

Natureza, na primeira versão: consumo, transferência entre contas próprias, reembolso, empréstimo. Só o consumo entra no resultado e nos gráficos. Os outros ficam visíveis e fora da soma, para não virarem receita ou despesa de consumo.

Situação: Pago ou A pagar; Recebido ou A receber. A data da nota não preenche a data em que o dinheiro se moveu. Uma nota de compra não prova quitação.

Moeda inicial declarada: BRL. Outro símbolo ou um valor no formato 10.00 fica em revisão. Não há conversão silenciosa.

Valor ausente não vira zero. Subtotal, desconto, troco e parcela não entram como total sem a pessoa reconhecer o campo.

Duas fotos do mesmo comprovante não são dois gastos. A possível duplicata usa, quando existirem, o identificador do documento, a imagem, o estabelecimento, a data e o valor juntos. O mesmo valor na mesma data, sozinho, não rejeita o lançamento. O aviso abre o registro existente ou deixa a pessoa confirmar que é outro.

Arquivar esconde o lançamento do mês e permite restaurar. Não há botão sem esse comportamento.

## Regras do mês

- Recebido entra pela data em que o dinheiro chegou.
- Pago sai pela data em que o dinheiro saiu.
- A receber e a pagar aparecem à parte, pela data prevista ou, se ela faltar, pela data da nota.
- Resultado = recebidos − pagos. Não se chama saldo disponível.
- Transferência, reembolso e empréstimo realizados no mês aparecem numa faixa própria e não alteram o resultado.
- Comprovante misto recebe uma categoria geral. A pessoa revisa. Não há rateio automático por item, e o modelo não impede essa evolução.

Categorias de gasto: alimentação, moradia, transporte, saúde, educação, lazer, compras, outras. De ganho: salário, serviços, outros. Dá para corrigir. Correções repetidas podem virar uma preferência daquela pessoa, explicável e reversível. Isso não é treinamento de um modelo individual.

## Contrato da leitura

A leitura devolve só o que conseguir identificar: estabelecimento ou descrição, data da nota, valor total, moeda e uma categoria sugerida. O que não identificar volta vazio, com um pedido de conferência em linguagem simples. Sem percentual de confiança inventado.

Estados previstos: processando, leitura boa, leitura parcial, imagem ilegível, falha de serviço, possível duplicata.

Processar ou enviar o arquivo não grava. Confirmar grava uma vez. Editar altera o mesmo lançamento. Cancelar descarta a sugestão.

O texto extraído é conteúdo do comprovante, nunca instrução para o sistema.

Arquivo aceito na implementação futura: JPEG, PNG ou WebP, até 8 MB, uma página na primeira versão. Fora isso, a leitura nem começa.

No protótipo 0.1.0 esses estados são exemplos sintéticos. Nenhuma imagem sai do navegador e nenhum serviço de IA é chamado.

## Isolamento

Autonomia, neste recorte, é acesso, navegação, identidade visual e dados pessoais separados. Não é um serviço pago novo.

Quando a implementação começar, o caminho recomendado é:

- aplicação e repositório de interface próprios da ISA;
- base própria, com dono em toda linha e toda imagem;
- diretório de identidade próprio, sem reutilizar o pool nem o cliente do ActionFinance;
- bucket privado próprio para comprovante, se a foto for guardada no servidor;
- nenhum registro pessoal criado como contraparte empresarial.

Reuso aceitável mais tarde, sem acoplamento: a conta AWS já existente, com recursos separados e outra política de acesso. Isso não se cria nesta etapa.

O protótipo atual guarda a demonstração só no `sessionStorage` do navegador, com duas pessoas fictícias (Marina Alves e Paulo Nunes) para mostrar que uma não lê a outra. Isso não substitui a autorização no servidor.

## Acesso, quando sair do protótipo

O protótipo entra sem senha, de propósito. A implementação não deve criar um depósito próprio de senha.

Opção recomendada: provedor de identidade gerenciado, com um diretório só da ISA. Cadastro, entrada, recuperação e saída ficam nesse provedor. O servidor da ISA recebe a identidade já verificada e filtra pelo dono. A recuperação de acesso é a do provedor, não um e-mail caseiro com senha gravada na aplicação.

Não usar o pool do Finance. Uma pessoa que também opera a empresa continua com duas identidades.

## Privacidade

- Dono verificado no servidor em lançamento, imagem e sugestão.
- Teste de aceitação: outro usuário autenticado pede o identificador e a imagem de Marina e recebe recusa, sem o arquivo.
- Comprovante pode ter CPF, endereço e detalhe sensível. Fica em endereço privado, sem URL pública.
- Log não recebe imagem, payload completo nem texto integral do cupom.
- Apagar a conta remove lançamentos, imagens e sugestões daquela pessoa, com prazo curto de restauração operacional antes do apagamento definitivo.
- Retenção do comprovante acompanha o lançamento. Arquivar não publica. Apagar remove.
- Antes de escolher o serviço de leitura: limite diário por pessoa, não reenviar a mesma imagem se a tentativa anterior ainda está em aberto, e custo por leitura visível para quem opera.

Nesta etapa não há envio a terceiro.

## Opções de leitura, para uma etapa posterior

Preços conferidos em 16/10/2026 nas páginas oficiais. Não contratar agora.

| Opção | O que a página oficial descreve | Preço visto | Leitura para a ISA |
| --- | --- | --- | --- |
| Amazon Textract AnalyzeExpense | Lê nota e recibo; devolve campos como fornecedor, total e itens. Há operação síncrona e assíncrona. O nível gratuito inclui 100 páginas por mês dessa API. | Exemplos oficiais em Oeste dos EUA (Oregon): US$ 0,01 por página até 1 milhão no mês; US$ 0,008 depois disso. | Melhor custo por comprovante de uma página. A conta AWS do ecossistema já existe, mas o comprovante pessoal precisa de bucket e permissão separados do Finance. Não criar isso agora. |
| Google Cloud Document AI, Expense Parser | Extrai campos de despesa. 1 count cobre até 10 páginas. | US$ 0,10 por count na tabela pública. | Mais caro para o cupom de uma página. Útil se a leitura do Google se mostrar melhor em nota brasileira, o que este documento não afirma. |
| OpenAI com entrada de imagem, por exemplo gpt-4.1-mini | Aceita imagem e devolve texto. O preço é por token, não por comprovante. | US$ 0,40 por 1 milhão de tokens de entrada e US$ 1,60 por 1 milhão de saída, na tabela de 16/10/2026. O custo da imagem depende do tamanho. | Não dá para prometer um custo fixo por nota. O texto do cupom iria ao provedor. Só cabe com contrato de retenção e com a imagem fora do log. |
| Azure AI Document Intelligence, modelo prebuilt de recibo | A documentação descreve comerciante, data, total e subtotal separados, e formatos JPEG, PNG, PDF e TIFF. | A página de preço oficial, nesta consulta, não entregou um número estável (a tabela veio sem valor). Não há preço de Azure neste plano. | Fica como alternativa até uma leitura direta da tabela numérica. |

Fontes: [Textract pricing](https://aws.amazon.com/textract/pricing/), [AnalyzeExpense](https://docs.aws.amazon.com/textract/latest/dg/analyzing-document-expense.html), [Document AI pricing](https://cloud.google.com/products/document-ai/pricing), [OpenAI pricing](https://developers.openai.com/api/docs/pricing), [Azure receipt](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/receipt).

Recomendação para a primeira implementação, ainda sem contratar: Textract AnalyzeExpense, uma página, com o total escolhido pelo tipo de campo e não pelo primeiro número da nota. A categoria continua sendo sugestão da ISA, a partir do estabelecimento e das correções daquela pessoa, não um lançamento automático. Se o custo ou a qualidade em cupom brasileiro não servir, a decisão volta para esta tabela antes de trocar de fornecedor.

## Extrato do Banco do Brasil

O perfil observado em 16/10/2026 está em `ISA_EXTRATO_BB_002.md`. A amostra real fechou em 53 movimentações e 11 observações de saldo. O protótipo demonstra a prévia com dados inventados. A conta não vem no arquivo: a pessoa declara o nome, em Real. Isso ainda não é a importação persistente.

## Identidade visual

Fundo branco suave, superfícies claras, acentos pastel de lavanda, azul e verde, texto escuro. A marca inicial é a palavra ISA. A sigla não tem expansão neste documento. Não há a faixa azul do Finance nem o menu lateral da tesouraria.
