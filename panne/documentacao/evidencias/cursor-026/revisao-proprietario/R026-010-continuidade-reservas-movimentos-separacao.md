# R026-010 — Continuidade reservas / movimentos / separação

## Estado

**Validada integralmente pelo Cortex** (após a terceira passagem).

## Passagens

| Passagem | Papel |
|---|---|
| 1ª | Enriquecimento de reservas, movimentos e leitura da separação |
| 2ª | Adoção de leitura somente e links por alocação |
| 3ª | Correção final da linguagem da limitação |

## Validação integral (Cortex)

### Reservas

Ordem pública e link; ingrediente; necessário/reservado/falta; situação; contexto histórico; alocações; links próprios LOT-000002 e LOT-000001.

### Movimentações

Data/hora; tipo; item; lote; local; sinais; unidade; documento; origem traduzida; auditoria recolhida; sem códigos crus.

### Separação

PICK-000001 com ordem/produto/status/data/responsável; linha (farinha, quantidade, lote, local); FEFO; conferência; impressão; mensagem humana de limitação; sem seletor/confirmação; sem mutação; sem jargão de API.

### Isolamento

Panne → Horizonte remove lista e detalhe; sem dados Panne residuais.

## Mensagem final (superfície)

`Nesta demonstração, você pode consultar e imprimir separações já confirmadas. A preparação de uma nova separação — necessidades, sugestão de lotes, revisão e confirmação — ainda não está disponível nesta tela.`

## Restrições observadas no registro

CURSOR-027 não iniciado. Sem commit/push/merge/deploy.
