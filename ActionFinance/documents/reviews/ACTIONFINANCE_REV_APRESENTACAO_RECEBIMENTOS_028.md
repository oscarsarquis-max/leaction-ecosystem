# Apresentação dos recebimentos enriquecidos — 028

Data: 15/10/2026. Baseline AF-BL-023 revisão 1.1. Produto publicado neste incremento: **0.1.2**. Aceite visual do proprietário: **não atribuído**.

Este recorte só muda a composição da lista, dos filtros, do resumo e do detalhe no Finance. Não altera valores, classificação, pendências persistidas nem a identidade dos pagamentos. Spider, Hub, Loja, Cognito, banco e a sincronização não foram modificados. A autorização do adapter no 027 não foi reutilizada.

## Identidade técnica do pagador

O checkout avulso grava, em `users.email`, um endereço montado assim: código da aplicação, um trecho em base64url do e-mail informado e o sufixo `@amount.hub.local`. Isso está em `leaction-platform/services/gateway-api/domain/amount-checkout.js`. O e-mail e o nome reais permanecem no payload do pedido. A lista que o Finance já consome prefere o e-mail da tabela `users`, então o identificador técnico chegou armazenado no papel de pagador.

A regra publicada reconhece só esse sufixo, já comprovado. Na lista e no título do detalhe o texto é **Pagador não identificado**. No rastreio técnico ficam a referência compacta e a frase: identificador gerado pelo checkout avulso para o cadastro interno, não é endereço de contato. O valor não foi apagado da persistência e não é tratado como contato.

E-mail que não termina nesse domínio continua como e-mail informado pelo ActionHub Pay. Outra identificação recebida, que não é e-mail, aparece como **Identificação recebida**, com o texto armazenado, sem o rótulo Cliente. Ausência continua **Pagador não identificado**. Não há decodificação do trecho técnico, nem nome inventado a partir do prefixo, nem classificação de e-mail desconhecido como técnico. O código `lojadepaes` aparece como **Loja de Pães**; o código armazenado permanece no detalhe. Código desconhecido continua como foi gravado.

Lacuna de contrato, fora deste recorte: para o Finance mostrar o contato real quando a origem o tem, a lista do Hub precisaria separar o e-mail do pedido da chave interna do checkout. Isso não foi feito. Não há heurística genérica no Finance para adivinhar essa separação.

## O que a tela passou a mostrar

Duas barras horizontais e o cabeçalho azul com a marca branca permanecem. Não há sidebar nem menu suspenso.

A lista larga tem sete colunas com largura definida: Recebimento, Pagador, Pagamento, Atualização na origem, Valores, Situação e Ação. Descrição longa fica em até duas linhas; o texto completo está no detalhe. Cobrado e Pago ficam separados, alinhados à direita, com dígitos tabulares. Ausência continua **Não informado**, sem virar zero. **Abrir detalhes** fica na mesma linha da ação. A referência curta e **Copiar referência** aparecem juntas.

Abaixo de 1024 px a tabela vira cartão, com aplicação, descrição, situação, valores, pagador, método e a ação. Os filtros continuam na página.

Os filtros saíram da fila única. Em tela larga ficam em grade: buscar referência, período **Atualização na origem** com De e Até, Situação, Pendência, Aplicação, Método e Limpar. O texto selecionado de Situação cabe no controle. A busca continua a filtrar a lista já carregada; o rótulo não promete busca por nome no servidor.

O resumo separa o que está armazenado da última tentativa. No exemplo sintético da captura: «4 registros · 2 com pendências» e «Última tentativa: 1 incluído · 11 atualizados». `UNPAID_EXPECTED` aparece no cartão e não entra na contagem de pendências, como já fazia o 027. Ambiente e o link da execução na Spider ficam em linha secundária. PRODUCTION não é apresentado como prova de pagamento real.

No detalhe, cobrado, pago e situação vêm primeiro. Depois aplicação, descrição, pagador, método, processador e datas. Referências, proveniência e histórico ficam em **Rastreio técnico**, identificado, sem esconder os valores.

## Comparação

| Antes, na captura do proprietário | Depois, nas capturas deste relato |
|---|---|
| Coluna Cliente longa comprimia origem e descrição em várias linhas | Recebimento e Pagador têm largura fixa; a descrição longa resume em duas linhas |
| Filtros cortavam o texto selecionado | Situação mostra «Aprovado na origem» por inteiro em 1280 px |
| Endereço `@amount.hub.local` aparecia como cliente | A lista diz «Pagador não identificado»; a natureza técnica fica no detalhe |
| Sair precisava ser conferido | Sair mede 44 px e permanece dentro de 360, 768, 1280 e 1848 px, com o nome longo visível |

As capturas usam dados sintéticos. Nenhum identificador real de pagamento entrou na fixture. O caso de R$ 90 da fixture cobra e paga 9000; isso não é o pagamento real.

## Capturas inspecionadas

Arquivos em `documents/reviews/screenshots/apresentacao-028/`. São o viewport, não a página inteira: a captura da página inteira colava o cabeçalho fixo sobre o conteúdo e foi descartada como evidência.

| Arquivo | O que foi visto |
|---|---|
| `lista-360.png`, `crop-header-360.png`, `crop-card-360.png` | Cabeçalho com marca, Loja de Pães, nome completo e Sair. Filtros em coluna. Cartão com descrição longa, e-mail real quebrado, Cobrado e Pago R$ 90,00, referência e Copiar referência. Sem rolagem horizontal da página |
| `lista-768.png`, `crop-header-768.png` | Cartões. Filtros em duas colunas. Sair visível |
| `lista-1280.png`, `filtro-situacao-1280.png`, `crop-header-1280.png` | Tabela de sete colunas. Filtros sem sobreposição. Situação selecionada legível. Três linhas após filtrar aprovados; a linha pendente na origem saiu do resultado |
| `lista-1848.png` | A mesma tabela com mais folga. E-mail longo cabe na coluna Pagador |
| `detalhe-90-1280.png` | R$ 90,00 cobrado e pago, situação primeiro, e-mail real com a natureza «E-mail informado pelo ActionHub Pay», Pix e Mercado Pago. Rastreio técnico fechado e identificado |
| `detalhe-tecnico-360.png`, `detalhe-tecnico-360-viewport.png` | Pagador não identificado, pendência de ambiente, referência e Copiar referência no rastreio aberto. O cabeçalho não cobre o primeiro conteúdo visível |
| `foco-1280.png` | Foco visível em Abrir detalhes depois de tabular a partir de Copiar referência, em viewport de 1600 px |

Medição automática em todas essas larguras: `scrollWidth` igual a `clientWidth`. Sair não cortado.

## Zoom de 200%

O Chromium usado na captura, headless e com janela, não aplica o zoom do navegador quando o atalho é enviado à página: `innerWidth` permaneceu 1280 e depois 1600. O fator de escala da página amplia sem reflow e corta o conteúdo; o arquivo `zoom-probe.png` mostra isso na tela de entrada e **não** é prova de zoom. `lista-zoom-200.png` é uma lista em 1600 px sem zoom. Viewport estreito também não foi usado como substituto.

O que o zoom do navegador faz é reduzir a largura em pixels de layout. Abaixo de 1024 px a lista já é de cartões. Essa composição foi medida em 360 e 768 px, sem rolagem horizontal da página e com Sair inteiro. Isso não substitui uma conferência humana com zoom real de 200% numa janela larga.

## Testes

| Suíte | Resultado |
|---|---|
| `PayReceiptsPage.test.tsx` | 7 testes, sucesso, inclusive identificador técnico fora da lista e e-mail real preservado |
| Captura da interface | Filtro de situação, Limpar, Abrir detalhes, Voltar, foco em Copiar referência e Tab |

Não rodei a suíte inteira do frontend nem `mvn verify`. O pacote Java desta imagem usou `-DskipTests` porque a lógica de sincronização não mudou. A suíte de cadastros que falhava antes deste recorte não foi reaberta.

## Dados persistidos

Leitura somente agregada, antes e depois da troca de imagem. Sem lista de identificadores e sem rótulo de pagador.

| Medida | Antes | Depois |
|---|---|---|
| Flyway | 20 | 20 |
| Recebimentos | 16 (12 PRODUCTION, 4 fora) | iguais |
| Pagos presentes / ausentes | 2 / 14 | iguais |
| Com aplicação | 12 | igual |
| Pagador e-mail / assunto / ausente | 12 / 0 / 4 | iguais |
| Pendências de PRODUCTION, pela mesma regra da tela | 10 | igual |
| md5 dos identificadores | `e131c29daeecfda9aff9e699c02f2448` | igual |
| md5 de valor, pago, ausência, classificação, status, aplicação, método e tipo de pagador | `ac1aafffe4745eac1376ba89f16d08f2` | igual |
| Títulos, baixas, movimentos | 0, 0, 0 | iguais |
| Última tentativa | SUCCESS, 1 incluído, 11 atualizados, 1 página | a mesma |

Não houve sincronização neste recorte. Os contadores da captura do proprietário (12 armazenados, 10 com pendências, 1 incluído e 11 atualizados) coincidem com PRODUCTION e com a última tentativa já gravada. Esta entrega não os criou e não os encerra como prova.

## Artefato publicado

| Peça | Anterior, rollback deste recorte | Publicado |
|---|---|---|
| Finance | `actionfinance-web:15` · `sha256:61cf094d2673d2344c293612b484e2c16cdb2d7cdc1458eebdab17a936e628cc` · SPA `index-UhuYx_ma.js` · produto 0.1.1 | `actionfinance-web:16` · `sha256:bcf11a54e4017cd5d4e64efce860ee1e47cfc716f77698980f8c3c33fbb34dec` · SPA `index-B0699gCh.js` · CSS `index-BBnoBM7d.css` · produto 0.1.2 |

O índice OCI da tag `apresentacao-028` é `sha256:4bb3af69b0260166696c24d32274c4c36db8e4147abf1ead6611ce2896b91d14`. A task usa o manifesto amd64, não o índice. JAR do host `sha256:47f6c770f2e3ea1e549671848ec0d9cef743b3b21f721d25d3977e4c65d645a3`. Flyway da task continua desligado. Rollout `COMPLETED`, desejado 1, em execução 1.

Conferido no ar: `GET /api/v1/system/info` devolve `version=0.1.2`, `RECEIPT_SYNC`, sincronização ligada. O JavaScript servido contém «Pagador não identificado», «Loja de Pães», «Copiar referência», «Identificação recebida» e «Atualização na origem». Spider e Hub não foram republicados.

Rollback: recolocar `actionfinance-web:15` no digest acima. A imagem anterior não apaga linhas nem o schema V20. Não há migration nova.

## Pendências que continuam abertas

O 027 pedia o detalhe do pagamento de R$ 90 na sessão autenticada e a repetição que não grava campo novo. Este acabamento não abre esse pagamento real e não dispara outra sincronização. Essas duas provas continuam abertas. Ausência de pendência financeira não significa pagador identificado nem conciliação concluída.

O zoom real de 200% do navegador não foi aplicado pela ferramenta. A composição que esse zoom seleciona abaixo de 1024 px foi medida; a conferência humana do zoom numa janela larga não foi feita.

Não há tag Git desta publicação. A próxima fatia de tesouraria continua sendo movimentos de conta a partir do extrato, e não faz parte deste release.
