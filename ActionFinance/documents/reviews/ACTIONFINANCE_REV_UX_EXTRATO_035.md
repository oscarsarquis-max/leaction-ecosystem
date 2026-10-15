# ACTIONFINANCE_REV_UX_EXTRATO_035

Data: 15/10/2026. Produto **0.2.1** publicado. Correção só de apresentação da jornada manual. Schema permanece V23. O arquivo real não foi importado. A sessão autenticada do host público não percorreu a tela. Spider, Hub, Mercado Pago e Cognito não foram alterados.

## Antes

As capturas citadas em `documents/reviews/screenshots/extrato-032/` não estavam no workspace. O código servido em 0.2.0 ainda tinha os comportamentos descritos: o texto de abertura falava de parser e de laboratório; a prévia repetia o aviso longo em cada pendência; o total era uma frase só; a coluna se chamava «Por que o total»; o detalhe dizia apenas «Data» e explicava a semântica num parágrafo.

## Depois

A abertura diz «Importe o relatório da sua conta para conferir as movimentações.» O formato fica ao lado de Importar arquivo. Perfil e parser ficam em Detalhes técnicos. Conta sem referência explica a dependência e usa o formulário que já existia. A prévia mostra arquivo, conta, período, data usada e as contagens. Antes do botão: todas as linhas são preservadas, as ambíguas ficam em revisão, e importar não realiza pagamento nem confirma conciliação. O aviso repetido virou um resumo com quantidade; o texto técnico abre em Motivo completo. «Resolvidas» saiu. Identificada não é classificada nem conciliada. O total parcial tem uma frase: «Considera apenas as linhas indicadas. Não representa o saldo da conta.» As colunas passaram a «Inclusão no total» e «Motivo da pendência», com «Identificação ambígua» na célula. O detalhe abre pelo líquido, direção e situação, com bruto e tarifa separados, e a data do perfil — «Data de aprovação» no relatório de liquidação.

## Ensaio isolado

Frontend em `127.0.0.1:5179` e backend de demonstração em `127.0.0.1:8091`, banco descartável. Fixture de 22 ocorrências. Conta sem vínculo, prévia, filtros, confirmação, lote, detalhe, voltar e reenvio. Desktop 1280 e celular 390. Zoom 2 no celular: a seção do extrato não ficou mais larga que ela mesma.

| Conferência | Resultado |
|---|---|
| Prévia | 22 lidas, 4 identificadas, 18 em revisão. Data de aprovação |
| Confirmação | 4 linhas, 22 ocorrências. Total parcial R$ 251,00 em 4 entradas |
| Títulos, baixas, movimentos | 14, 3 e 7 antes e depois |
| Reenvio | a prévia abre de novo. «IS_RELEASED» não aparece fechado |
| Detalhe | líquido primeiro, data de aprovação, sugestão ainda sem conciliação |

## Publicação

Código `f4d40f019b38bfdabe7efb5e018606c1524756d0`.

| Peça | Valor |
|---|---|
| Task | `actionfinance-web:18` |
| Índice | `sha256:9335ddb372b892f9bab06e197f1228c83b10663c463099ff5940467df829697a` |
| Imagem linux/amd64 | `sha256:e6b0e865e8e56fff213c8bb1a86fe1a73cfa328697e1ea1dcfaaf637cee403b8` |
| JAR | `sha256:984661f70e7fb74bcd42436468e1815f647298551a0c4e0763b1f820b37354e0` |
| Bundle servido | `/assets/index-JjqQdVrO.js` |
| Rollout | `COMPLETED`, desejada 1, `HEALTHY`, Flyway da task `false` |
| `system/info` | `version=0.2.1` |
| Extrato sem sessão | shell 200; linhas 401 |

O bundle servido contém a frase nova de abertura e não contém «Por que o total» nem «Resolvidas».

Rollback da aplicação: `actionfinance-web:17`, `sha256:2e6ccb8fed8dd65f7b1547a1ef65cd8c0ff70b889454163b536f066183ecd31f`, produto 0.2.0, bundle `index-DzYbnxZv.js`. Voltar a imagem não apaga o schema.

O aceite visual continua com o proprietário. A inspeção autenticada do host público não foi feita.
