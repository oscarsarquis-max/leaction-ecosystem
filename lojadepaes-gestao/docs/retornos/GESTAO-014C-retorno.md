# GESTAO-014C — retorno

Base: `feat/gestao-014b-comanda` (`c30d1746`). Branch: `feat/gestao-014c-numeros`. Sem migração. O Gestão continua no mesmo host da Loja.

## De onde saíram os números da demonstração

A comanda do 014B não saiu do cálculo. O `comanda-a4.pdf` foi montado à mão no roteiro de captura: o título (112 un, peças de 568 g, massa 36,65 kg) e as linhas (farinha 20 kg, água 14 kg, sal 400 g, inóculo 5,60 kg) foram escritos separados, sem receita publicada, sem peso final, sem perda e sem fator.

| Campo | O que a foto mostra | Conta |
|---|---|---|
| Receita publicada | não há | a captura não leu receita |
| Peso final | não há | |
| Perda de processo e de cocção | não há | |
| Peso cru por peça | 568 g | digitado |
| Massa no título | 36,65 kg | digitado. Era o exemplo de formato do 014B, não o resultado de 112 × 568 |
| Fator | não há | |
| Farinha, água, sal, inóculo | 20 + 14 + 0,4 + 5,6 = 40,0 kg | digitados, um a um |

112 × 568 g são 63,616 kg só de peças cruas. 36,65 kg não cobre isso, e 40,0 kg de ingredientes também não é 36,65 kg.

A frase: a captura preencheu o título e os ingredientes à mão, então as duas contas nunca foram a mesma.

A regra que a comanda passa a usar é `unidades × peso cru ÷ (1 − processo)`, com o total arredondado ao grama. Para 112 peças de 568 g e 5 % de processo: 112 × 568 ÷ 0,95 = 66.964 g, exibidos como **66,96 kg**. Os 66,98 kg do enunciado aparecem se cada peça for arredondada antes (568 ÷ 0,95 ≈ 598 g, e 598 × 112 = 66.976 g). A conta do serviço segue a fórmula escrita, e o teste afirma 66,96 kg.

## Checklist

1. **Feito.** A explicação e a tabela estão acima. A soma dos ingredientes da demonstração (40,0 kg) não é a massa do título (36,65 kg) porque os dois números foram inventados na captura, não calculados.

2. **Feito.** Só os testes novos: `tests/test_comanda_014c.py`, 4 passaram. 112 peças de 568 g com 5 % de processo dão massa 66,96 kg e a soma dos ingredientes fica dentro de 0,5 %. Uma foto antiga com a massa pela metade ganha o aviso "Conta não fecha", o bloco continua e a farinha não é recalculada; o aviso também vai para o log. A consolidação de 100 + 12 da mesma receita usa peça de 568 g, processo de 5 % e massa 66,96 kg. Duas fotos de receita diferente mostram "receitas diferentes nas ordens", com a lista de ingredientes vazia, sem somar às cegas.

3. **Feito.** `docs/evidence/gestao-014c-local/comanda-a4.pdf`: Pão country 112 un, peças de 568 g, massa 66,96 kg, farinha 46,96 + água 18,00 + sal 2,00. Baguete 40 un, peças de 320 g, massa 14,22 kg, farinha 14,22 kg. O caso forçado, só local, está em `comanda-aviso.png`: o bloco do Pão country permanece e o aviso "Conta não fecha: ingredientes 40,00 kg × massa 36,65 kg. Revise a receita" aparece no bloco e na faixa, antes de imprimir. O diálogo do botão Imprimir repetiu o mesmo texto.

4. **Feito** o Dia, em `dia-1280.png` e `dia-390.png`. "100 programadas · 12 da Loja" aparece uma vez, na coluna Origem, numa linha só. Embaixo do produto, a contagem desse texto é zero. **Não feito** a medida do 016A em produção. `https://gestao.lojadepaes.com.br/produtos` abre em "Entrar". A senha não está na leitura autorizada deste ciclo (o banco `gestao`, sem segredo). Não medi o retângulo, para não inventar o número.

5. **Feito.** Imagem `lojadepaes-gestao:014c-20261111`, sem Alembic. Só o `gestao-api` foi recriado. `https://gestao.lojadepaes.com.br/` responde 200 e serve `index-DkT3Jlsb.js`, SHA-256 `aa24c17a977ea4f406d706a4f2018f9abb8aee7aa5b4c3d0e500bbf63fd5f1e5`, igual ao pacote da imagem. `https://lojadepaes.com.br` responde 200, com o JavaScript da vitrine que já estava no ar (`index-BPpk5tJI.js`). A contagem da Loja ficou igual antes e depois: `media_assets` 17/0/0, `product_variants` 16/6/6, `products` 16/35/6, `showcase_slots` 10/16/0. O Alembic continua em `0012_cultura_viva`. A porta 22 aberta neste ciclo foi fechada (`regras_22` 0). O grupo do Hub não foi alterado.

O commit desta branch leva o código, este retorno, as capturas e o PDF.

A imagem anterior, para voltar, é `lojadepaes-gestao:014b-20261111`. O banco não mudou.
