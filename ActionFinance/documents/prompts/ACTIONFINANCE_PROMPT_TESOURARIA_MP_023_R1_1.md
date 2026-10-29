# Tesouraria e análise financeira com Mercado Pago

ACTIONFINANCE_PROMPT_TESOURARIA_MP_023 revisão **1.1**. Data 15/10/2026. Substitui a orientação de execução da revisão 1.0. Não é versão 1.1 do produto e não autoriza publicar tesouraria.

A revisão 1.0 permanece em [ACTIONFINANCE_PROMPT_TESOURARIA_MP_023.md](ACTIONFINANCE_PROMPT_TESOURARIA_MP_023.md), hash `775B9CBD467B5F073FD73A3B01943D5A02E3BF0589B9EE2553B1D0662E20D073`.

## Restrição

Manter a Spider íntegra. Não alterar código, contrato, schema, catálogo, adapter, configuração, credencial, banco, Monitor, infraestrutura ou implantação. Não reiniciar nem republicar serviços da Spider. Não enfraquecer o isolamento entre produção e sandbox.

O percurso continua Finance → Spider → Hub → Spider → Finance, só com capacidades já disponíveis. Sem fallback Finance → Hub ou Finance → Mercado Pago. A Loja e os planos do Hub são outro percurso.

Inspeção da Spider é somente leitura. Sincronização já autorizada pode ser chamada. Não testar indisponibilidade nem reconfigurar a Spider. Campo que não atravesse o contrato atual fica como dependência, sem contorno.

## Sequência

Registrar obrigações no Finance, pagar no Mercado Pago e conciliar depois. O Finance não executa o pagamento nesta etapa.

Primeiro, a integridade dos recebimentos da empresa `624023a4-57e3-415c-b7d0-925ca1acd3b7`. O caso de referência é o pagamento `b6cf9b7a-d8d3-42a7-873e-818f17133322` (R$ 90 de cobrado). Não construir indicador sobre dado cuja origem não esteja demonstrada.

Versionamento do Prompt 024: revisão de requisito, versão de produto, schema e implantação são eixos distintos.

## O que esta revisão autoriza

Integridade e sincronização já autorizadas, até a prova pública, sem mudar a Spider. Para tesouraria nova: inspeção, projeto, contratos propostos, regras e prévia com dado sintético. Não autoriza movimentar dinheiro, iniciar pagamento, importar extrato em produção, alterar saldo inicial ou criar infraestrutura paga.
