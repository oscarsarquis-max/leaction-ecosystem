# ISA — plano de implementação

Baseline 1.0. O protótipo 0.1.0 não é esta implementação. Nada aqui publica, cobra ou envia comprovante.

A tesouraria empresarial permanece no ActionFinance 0.2.10. Esta frente não incrementa essa versão.

## Ordem depois do protótipo 0.4.0

A importação local sintética está fechada no protótipo 0.4.0: a decisão vem antes da lista, a pendência continua acessível e o resultado só soma natureza identificada. O protótipo 0.5.0 acrescenta o planejamento local descrito na fatia 4. A base e o dono já existem no laboratório. O diretório de identidade real continua pendente; sem ele não há acesso de pessoa de verdade. A categorização real depende do provedor escolhido e não impede usar a importação nem o planejamento. Open Finance e atualização automática ficam para outra frente.

## Perfil do extrato, já no protótipo

O leitor do Banco do Brasil está em `prototype/bb-statement.js`, com fixture sintética e testes. A amostra real foi lida só localmente: 53 movimentações, 11 observações de saldo, controle fechado. A conta de destino é declarada pela pessoa, em Real, porque o CSV não traz agência nem conta. Guardar isso no produto, com dono e conta no servidor, continua na fatia de lançamentos. O protótipo não é essa gravação.

## Fatia 1 — Acesso e lançamentos

Entra uma pessoa, grava ganho e gasto digitados, vê o mês e corrige o mesmo lançamento.

- Diretório de identidade só da ISA, gerenciado, sem senha guardada na aplicação e sem o pool do Finance.
- Base própria. Toda linha tem dono. A consulta filtra no servidor.
- Lançamento com direção, natureza, valor em centavos, moeda BRL, categoria, situação e as três datas (nota, situação, previsão).
- Mês: recebidos e pagos pelo dia em que o dinheiro se moveu; a receber e a pagar à parte; transferência, reembolso e empréstimo fora do resultado.
- Arquivar e restaurar.
- Testes: Marina não lê o lançamento nem o identificador de Paulo; resultado de outubro com os casos sintéticos do `prototype/calc.test.mjs`; editar não cria outro id; valor vazio não vira zero.

Dependência real: o diretório de identidade. O protótipo não espera por ela.

## Fatia 2 — Captura e leitura confirmável

A pessoa fotografa ou escolhe uma imagem. A leitura sugere. Confirmar grava uma vez.

- Site responsivo, sem aplicativo. Câmera do navegador, com galeria e digitação se a permissão falhar. O protótipo não comprova a câmera do aparelho.
- Arquivo JPEG, PNG ou WebP, até 8 MB. Fora disso, a leitura não começa.
- Serviço candidato, ainda sem contrato: Amazon Textract AnalyzeExpense, uma página, bucket e permissão separados do Finance. Preço de referência conferido em 16/10/2026: US$ 0,01 por página até 1 milhão no mês, na região citada na página oficial, e 100 páginas por mês no nível gratuito. Ver `ISA_PROJETO_MVP_001.md`.
- O total só entra se o campo for o total. Subtotal, desconto, troco e parcela ficam de fora.
- Estados: processando, boa, parcial, ilegível, falha, possível duplicata.
- Duplicata por identificador do documento, imagem, estabelecimento, data e valor. O mesmo valor na mesma data não rejeita sozinho.
- Não reenviar a mesma imagem enquanto a tentativa anterior não terminou. Limite diário por pessoa. Log sem imagem e sem texto integral.
- Testes: processar não grava; confirmar grava uma vez; segunda foto do mesmo documento abre o existente; falha do serviço deixa o rascunho intacto; outro usuário não baixa a imagem.

Dependência real: a conta do serviço de leitura e o bucket privado. Sem isso, a fatia 2 fica no modo manual, que a fatia 1 já entrega.

## Fatia 3 — Categoria e resumo

- Categorias simples, editáveis, sem vocabulário contábil.
- Sugestão a partir do estabelecimento e das correções daquela pessoa. A preferência é uma regra visível, que ela pode desfazer. Não é modelo treinado.
- Comprovante misto: uma categoria, revista pela pessoa.
- Início com o mês, o gráfico de gastos pagos e a abertura de cada número nos lançamentos que o formam.
- Testes: correção repetida passa a sugerir a categoria escolhida só para aquela pessoa; Paulo não herda a preferência; a receber não entra no resultado.

## Fatia 4 — Planejar o mês

O protótipo 0.5.0, baseline proposta 1.2, responde se o dinheiro chega até a próxima entrada. O detalhe está em `ISA_PROJETO_PLANEJAMENTO_004.md` e a verificação em `ISA_REV_PLANEJAMENTO_004.md`.

- Disponibilidade com data, entrada prevista, compromisso, reserva e cenário ficam em tabelas próprias, com dono e origem. Um saldo antigo do extrato não vira dinheiro disponível.
- O motor usa centavos e datas civis. A data de referência dos testes é 16/10/2026. Terminar o mês positivo não esconde a falta do meio do caminho.
- Início aponta a informação que falta ou o próximo aperto. Planejar compara uma data alternativa. Guardar o plano escolhido não muda o vencimento nem paga nada.
- A base local é SQLite, servida em `127.0.0.1:8098`. A identidade sintética só funciona com `ISA_ENV=lab`. Configuração de produção recusa esse mecanismo.
- As explicações desta etapa são regras demonstrativas. Nenhum provedor é chamado e nenhuma sugestão vira lançamento sozinha.

O que esta fatia ainda não entrega: cadastro real, senha, diretório próprio da ISA e agente de linguagem contratado. As telas de importação do 0.4.0 continuam na demonstração do navegador; a API de importação do servidor foi provada com fixtures sintéticas e não copia o que já estava na sessão.

A preparação do piloto, sem publicação, está em `ISA_PLANO_IMPLANTACAO_004P.md` e `ISA_RECUPERACAO_004P.md`. O Prompt 005 continua reservado aos cartões.

## Publicação, quando houver aprovação

1. Aprovar o protótipo visual.
2. Implementar a fatia 1 num endereço próprio, ainda sem comprovante real.
3. Só então decidir o serviço de leitura e criar o bucket separado.
4. Publicar a leitura com o limite diário e sem cobrança ao usuário nesta baseline.

Recuperação: a versão anterior da aplicação da ISA volta ao ar sem tocar na task `actionfinance-web`. Os dados pessoais não moram no banco do Finance, então o retorno do Finance não restaura nem apaga a ISA.

## Critério de aceite da implementação

Uma pessoa, no celular, registra um gasto digitado, confere, vê o valor no mês, troca a categoria e não ganha um segundo lançamento. Fotografa um comprovante sintético, corrige um campo e confirma. Uma segunda foto do mesmo documento oferece o lançamento que já existe. Um ganho recebido e um valor previsto aparecem separados. O resultado do mês não é chamado de saldo. Outra pessoa autenticada não abre esses registros nem essas imagens.
