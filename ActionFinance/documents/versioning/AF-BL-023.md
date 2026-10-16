# AF-BL-023 — Baseline de requisitos

| Campo | Valor |
|---|---|
| Identificador | AF-BL-023 |
| Revisão | **1.0** |
| Data da decisão | 09/10/2026 |
| Autoria da decisão | Proprietário do produto |
| Prompt de origem | ACTIONFINANCE_PROMPT_TESOURARIA_MP_023 |
| Arquivo canônico (não reescrito) | [prompts/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023.md](../prompts/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023.md) |
| Cópia imutável desta revisão | [baselines/AF-BL-023/1.0/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023.md](baselines/AF-BL-023/1.0/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023.md) |
| SHA-256 (SHA256, arquivo UTF-8) | `775B9CBD467B5F073FD73A3B01943D5A02E3BF0589B9EE2553B1D0662E20D073` |
| Tamanho do arquivo na adoção | 8653 bytes |
| Projeto executivo associado | [ACTIONFINANCE_PROJETO_TESOURARIA_MP_023](../architecture/ACTIONFINANCE_PROJETO_TESOURARIA_MP_023.md) — **não** faz parte do texto aprovado do prompt; não altera o hash |

Esta revisão **identifica requisitos**. Não afirma que tesouraria, conciliação ou posição de caixa estejam implementadas.

A orientação de execução vigente é a revisão **1.4** (16/10/2026), registrada abaixo. As revisões 1.0, 1.1, 1.2 e 1.3 permanecem o histórico.

Mudança futura da baseline: novo prompt, nova revisão (1.1+), hash próprio, diferença explícita em relação a 1.0. Não editar o arquivo da 1.0.

## Pendências vinculadas (abertas)

Não encerradas por esta baseline.

| Pendência | Prompt / evidência | Vínculo |
|---|---|---|
| Integridade dos recebimentos (pagador, pago, método; prova pública do ID `b6cf9b7a…`) | 019 — [REV_INTEGRIDADE_RECEBIMENTOS_019](../reviews/ACTIONFINANCE_REV_INTEGRIDADE_RECEBIMENTOS_019.md) | Continua; V20 local não publicada |
| Dados recuperados / contratos de captura de recebimentos | 021 (autorização vigente) | Continua |
| Rastreabilidade / Monitor (persistência RAM 24h/2000; prova pública da execução) | 020 | Continua |
| Aplicação analítica 022 além deste recorte | 022 | Direção; não implementada |

## O que a 1.0 não inclui como implementado

Pagamento pelo Finance; conector MP automático; extrato persistido; três bases de saldo no produto; projeção; alteração de OPENING produtivo.

## Revisão 1.1 — orientação de execução

| Campo | Valor |
|---|---|
| Revisão | **1.1** |
| Data | 15/10/2026 |
| Efeito | Substitui a orientação de execução do 023. Não é versão 1.1 do produto e não autoriza publicar tesouraria |
| Arquivo | [prompts/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023_R1_1.md](../prompts/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023_R1_1.md) |
| SHA-256 | `D372E02C83202FB820A6277073AAABFDBD7F07BB56D17B89593A7BBD602AE986` |
| Tamanho | 2083 bytes |
| Cópia | [baselines/AF-BL-023/1.1/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023_R1_1.md](baselines/AF-BL-023/1.1/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023_R1_1.md) |
| Restrição | A Spider permanece íntegra. Nenhuma alteração de código, contrato, configuração ou implantação |
| Relato de integridade | [REV_INTEGRIDADE_BASELINE_023_R1_1](../reviews/ACTIONFINANCE_REV_INTEGRIDADE_BASELINE_023_R1_1.md) |
| Projeto | [PROJETO_TESOURARIA_MP_023_R1_1](../architecture/ACTIONFINANCE_PROJETO_TESOURARIA_MP_023_R1_1.md) |

Diferença em relação à 1.0: a primeira entrega passa a ser a integridade dos recebimentos já sincronizados, com a Spider congelada. Tesouraria nova fica em projeto, prévia e regras, sem extrato produtivo, pagamento ou saldo inicial.

## Revisão 1.2 — orientação de execução

| Campo | Valor |
|---|---|
| Revisão | **1.2** |
| Data | 15/10/2026 |
| Efeito | Substitui a orientação de execução da 1.1. Não é versão de produto e não autoriza importar extrato, pagar, alterar saldo ou mudar a Spider |
| Arquivo | [prompts/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023_R1_2.md](../prompts/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023_R1_2.md) |
| SHA-256 | `2568D074BD58222010EF35CE1ADB68392605C53CAFA8F76E7A1CC03484FAEBFC` |
| Tamanho | 7560 bytes |
| Cópia | [baselines/AF-BL-023/1.2/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023_R1_2.md](baselines/AF-BL-023/1.2/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023_R1_2.md) |
| Projeto | [PROJETO_TESOURARIA_MP_023_R1_2](../architecture/ACTIONFINANCE_PROJETO_TESOURARIA_MP_023_R1_2.md) |
| Plano | [PLANO_ENTREGA_TESOURARIA_023_R1_2](../architecture/ACTIONFINANCE_PLANO_ENTREGA_TESOURARIA_023_R1_2.md) |

Diferença em relação à 1.1: a observação de cobrança publicada no 027 e a apresentação 0.1.2 permanecem. A próxima fatia preparada é extrato por arquivo e sugestão de vínculo com os recebimentos já gravados. Rateio padrão «Não atribuída» e iniciativas da mesma empresa deixam de ser pergunta. Importação produtiva, saldo inicial e capacidade nova da Spider continuam sem autorização.

## Revisão 1.3 — preservada

| Campo | Valor |
|---|---|
| Revisão | **1.3** |
| Data | 16/10/2026 |
| Estado | Histórico de execução. O índice já registrava esta revisão e o hash `733E99A930B4BB6718BF7D87AB7DDD4A696FEF4CC507A70633CBC0D355956E39`. Esta seção não apaga esse registro |

## Revisão 1.4 — fechamento da classificação e da jornada

| Campo | Valor |
|---|---|
| Revisão | **1.4** |
| Data | 16/10/2026 |
| Efeito | Acrescenta o que os incrementos 049 e 050 implementam. Não apaga 1.0 a 1.3 e não é aceite do proprietário |
| Produto | Candidata 0.2.8, sobre a 0.2.7 que estava no ar |

O que esta revisão pode anunciar como capacidade do código: classificação e rateio confirmados pelo operador, conciliação do livro distinta da referência comercial, resumo e agenda da tesouraria sobre títulos já cadastrados, e a revisão visual das jornadas de recebimento e pagamento.

O que continua fora: posição informada pela fonte, conta prevista no compromisso, fluxo de caixa projetado, análise e planejamento. A posição mostrada é a do livro até a data, só das contas ativas em real cujo saldo inicial já vale nessa data.
