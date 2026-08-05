# QMind — Plano de descoberta e piloto consultancy-led

- Status: **Piloto controlado autorizado** (2026-08-04) — homolog aprovada; observação 7d em paralelo; produção ampla não autorizada
- Data de abertura: 2026-08-04
- Decisão de origem: `012_Business_Model_and_Product_Focus.md`
- ADR: `../05_ADR/ADR-011-consultancy-led-platform.md`
- Ambiente: `app.homolog.qmind.com.br` (ver gate `011` + `OBSERVATION_7D_20260804.md`)

## 1. Objetivo

Validar se consultores e empresas de consultoria adotam e pagam pelo QMind para conduzir avaliações, e se organizações clientes demonstram interesse em continuar utilizando o workspace após o projeto.

## 2. Hipóteses

| Código | Hipótese | Evidência mínima |
|---|---|---|
| H1 | Consolidação e relatório consomem tempo relevante do consultor | Entrevistas + linha de base de horas |
| H2 | Rastreabilidade e padronização geram valor percebido | Problema citado espontaneamente e demonstração validada |
| H3 | Uma consultoria precisa operar múltiplas organizações | ≥3 entrevistados confirmam fluxo recorrente |
| H4 | Cliente aceita participar do workspace | Ao menos um piloto com usuário do cliente |
| H5 | Cliente deseja continuidade após o diagnóstico | Pedido explícito + atividade após entrega |
| H6 | Offline/captura em campo é decisivo para parte do mercado | Frequência e cenários documentados |
| H7 | IA economiza tempo sem comprometer confiança | Comparação de tempo + taxa de edição/rejeição |
| H8 | Existe disposição a pagar | Carta de intenção, piloto pago ou proposta aceita |

## 3. Perfis para entrevistas

- 5 a 8 consultores independentes.
- 3 a 5 empresas de consultoria.
- 5 gestores da qualidade de organizações atendidas.
- 2 a 3 auditores internos ou externos, sem misturar certificação e consultoria.

Os números são metas de descoberta, não amostra estatística.

## 4. Roteiro de entrevista

Perguntar sobre trabalho real recente, evitando perguntas hipotéticas:

1. Como foi a última avaliação do início à entrega?
2. Onde foram registradas perguntas, respostas, fotos e documentos?
3. Quanto tempo foi gasto em campo e depois dele?
4. Onde ocorreram retrabalho, perda de contexto ou inconsistência?
5. Como o cliente recebeu e acompanhou as ações?
6. Quantos clientes e avaliações são conduzidos simultaneamente?
7. O que precisa funcionar sem conexão?
8. Quem deveria ser proprietário dos dados?
9. O que acontece com os registros ao fim do contrato?
10. Como o serviço é cobrado hoje e qual unidade faria sentido para software?

Somente após compreender o processo atual deve-se demonstrar o QMind.

## 5. Piloto proposto

- Uma consultoria parceira.
- Uma organização cliente.
- Uma avaliação ISO 9001 real e autorizada.
- Duração estimada: um ciclo completo de avaliação.
- Infraestrutura econômica de homologação/piloto.
- Suporte próximo e canal único de incidentes.

O piloto não deverá usar conteúdo normativo sem licença nem dados pessoais desnecessários.

## 6. Linha de base e métricas

Antes do piloto:

- horas de preparação;
- horas de campo;
- horas de consolidação e relatório;
- ferramentas utilizadas;
- número de correções do relatório;
- tempo até aceite do plano;
- custo estimado do processo atual.

Durante e depois:

- tempo nas mesmas etapas;
- percentual do fluxo realizado no QMind;
- constatações com rastreabilidade completa;
- falhas, bloqueios e necessidade de suporte;
- uso e custo de armazenamento;
- chamadas, tokens, custo e aceitação da IA;
- participação do cliente;
- intenção de continuar e pagar.

## 7. Experimentos comerciais

Comparar sem compromisso definitivo:

- preço por profissional;
- preço por organização ativa;
- preço por avaliação;
- plano de consultoria com franquia;
- continuidade paga pela organização após handoff.

Registrar reação, objeção, facilidade de compreensão e impacto sobre margem da consultoria.

## 8. Critérios de decisão

### Prosseguir consultancy-led

- problema frequente e caro confirmado;
- fluxo completo utilizado no piloto;
- ganho mensurável de tempo ou qualidade;
- disposição a pagar;
- necessidade de múltiplas organizações confirmada.

### Investir em continuidade SGQ

- organização mantém usuários ativos após entrega;
- ações continuam sendo atualizadas;
- demanda recorrente converge em capacidades comuns;
- assinatura própria é aceita.

### Revisar ou interromper

- problema pouco frequente;
- ganho não mensurável;
- adoção depende de customização por cliente;
- custo de suporte ou IA inviabiliza preço;
- propriedade e acesso não encontram modelo aceitável.

## 9. Backlog condicionado à descoberta

Não iniciar antes da evidência correspondente:

| Capacidade | Condição |
|---|---|
| ConsultancyWorkspace | H3 confirmada |
| Handoff e transferência | H4/H5 confirmadas |
| Offline amplo | H6 confirmada |
| Templates por consultoria | Repetição real de método |
| Cobrança automatizada | Modelo e preço validados |
| Módulos SGQ recorrentes | Uso pós-projeto confirmado |
| IA adicional | Economia e qualidade comprovadas |

## 10. Entregáveis

- Notas anonimizadas das entrevistas.
- Mapa do processo atual.
- Linha de base de tempo e custo.
- Relatório do piloto.
- Decisão de preço inicial.
- Emenda do modelo de domínio, se aprovada.
- Roadmap revisado por evidências.

## 11. Gate de encerramento

O ciclo termina com uma decisão registrada:

- prosseguir;
- prosseguir com ajustes;
- pivotar segmento/proposta;
- interromper hipótese.

Nenhuma dessas decisões será inferida apenas por interesse verbal; deverão ser consideradas comportamento no piloto, uso, ganho mensurável e disposição a pagar.

