# SPIDERBANK-ARQ-003
## Arquitetura de implementação — SpiderBank como Experience Satellite de Crédito

**Status: LIBERADO PARA IMPLEMENTAÇÃO DO ESCOPO DESTE DOCUMENTO**  
**Versão:** 1.1  
**Data:** 18 de setembro de 2026  
**Destinatário:** Cursor  
**Cópia de referência:** este arquivo é a cópia operacional do documento autorizado pelo usuário. Não substitui ADR-001, ARQ-002 nem CONTRACT-001.

A primeira entrega (IMP-001) permanece histórica: jornada SAT-003 até `PLAN_IMPEDED`, sem despacho ao mock. A segunda entrega (ARQ-004 / IMP-002) executa o plano demonstrativo com o mock registrado no recorte `local-demo`.

## 1. Ordem de implementação

Implementar o SpiderBank como aplicação independente em `C:\Projetos\spider-bank`, usando o mesmo processo de integração do SegSense com o Spider.

**Primeira entrega definida:** satélite EXPERIENCE com frontend e BFF próprios, contexto de crédito governado, confirmação do objetivo, chamada ao Satellite Contract e apresentação fiel dos resultados ou impedimentos retornados pelo Spider.

Essa entrega não promete simulação ponta a ponta. As seis capabilities de crédito sem execução governada continuam indisponíveis. Não saltar pré-requisitos para alcançar o mock.

São autorizadas as alterações necessárias no Spider para integrar esta primeira jornada. O conector do sistema de crédito e a ampliação dos mocks dos pré-requisitos não fazem parte desta execução. O mock existente permanece preservado.

## 2. Arquitetura obrigatória

**Cliente → frontend SpiderBank → BFF SpiderBank → Satellite Contract → Spider → plano/capabilities → resolução e execução quando disponíveis → Spider → BFF → frontend.**

SpiderBank conhece cliente, experiência e domínio de crédito. Spider determina Intent canônico, políticas, plano, capabilities, resolução e execução.

IA é opcional antes do Intent Contract. Esta fatia usa interpretação determinística.

## 3. Estrutura da aplicação

| Diretório | Conteúdo |
|---|---|
| `frontend/` | Experiência de crédito e testes. |
| `backend/` | BFF, validações, integração com Spider e testes. |
| `database/` | Sem persistência nesta entrega. |
| `documents/` | Arquitetura, execução e evidências. |
| `scripts/` | Inicialização, encerramento e verificações locais. |
| `services/` | Apoio à integração contratual com Spider. |

Portas próprias: BFF `:8090`, frontend `:5190`. Não copiar segredos, identidade visual ou domínio de seguros.

## 4. Identidade, finalidade e objetivo

- Identidade: `spiderbank`
- Papel: `EXPERIENCE`
- Finalidade: `WORKING_CAPITAL_ASSESSMENT`
- Declaração reconhecida: `SEEK_WORKING_CAPITAL`
- Plano existente: `WORKING_CAPITAL_DIAGNOSTIC_V1`

O BFF não escolhe o Intent canônico. Entradas incompatíveis recebem o tratamento contratual, sem adivinhação.

A finalidade futura do provider `WORKING_CAPITAL_SIMULATION` permanece separada.

## 5. Integração pelo Satellite Contract

O BFF chama `POST /v1/satellites/interactions` (contrato 1.0, menor extensão compatível):

- `X-Spider-Satellite-Id`
- `X-Spider-Satellite-Secret`
- `X-Correlation-ID`
- `Idempotency-Key`

Credenciais ficam somente no servidor. Não usar `GET /v1/demo/spiderbank/entry` nem `POST /v1/demo/spiderbank/understand` como substitutos. Não remover esses endpoints legados.

## 6. Contexto governado

Fonte sintética registrada: `SPIDERBANK_WORKING_CAPITAL_SYNTHETIC_V1`.

Marcadores emitidos somente porque o mecanismo existe: `SATELLITE_GOVERNED`, `GOVERNED`, `SERVER_REGISTRY`.

A fonte não substitui perfil cadastral, perfil de crédito ou elegibilidade.

## 7. Plano existente e disponibilidade

O plano obrigatório de sete passos permanece. Não criar plano paralelo. Não marcar capabilities como AVAILABLE.

`IDENTIFY_CUSTOMER` não é concluída sem principal autenticado do cliente. A identidade técnica do satélite não identifica o cliente.

## 8. Experiência mínima

1. Apresentar a situação demonstrativa e a origem do contexto.
2. Solicitar confirmação explícita do objetivo.
3. Enviar a interação pelo BFF ao Spider.
4. Exibir o resultado e as pendências reais.
5. Permitir nova tentativa em falha transitória.

Não mostrar produto, taxa, limite, carência, aprovação, proposta ou contratação.

## 9. Tratamento de resultados e falhas

| Situação | Comportamento |
|---|---|
| Contexto ausente ou objetivo ambíguo | Complementação específica segundo o contrato. |
| Política rejeita a interação | Bloqueio comunicado com a explicação permitida. |
| Capability indisponível | Impedimento retornado pelo Spider, sem simulação substituta. |
| Spider inacessível ou timeout | Indisponibilidade técnica, sem classificá-la como recusa de crédito. |
| Resposta inválida ou correlação divergente | Falha de integração. |

HTTP 200 isoladamente não equivale a aprovação ou conclusão de análise.

## 10–12. Limites

Não integrar `mock-sistemas-credito` nem a porta `8096`. Não habilitar o card SpiderBank da Simulação. Não introduzir banco de dados. MOCK_ONLY e SIMULATED_INFRASTRUCTURE.

## 13. Critério de conclusão desta fatia

**SpiderBank integrado como Experience Satellite, com contexto governado e diagnóstico fiel dos impedimentos da primeira jornada.** Não declarar simulação de crédito ponta a ponta.

## 16. Baseline

A disponibilidade da jornada completa na Simulação depende do caminho pelo provider. A interação de diagnóstico deve aparecer no Monitor com identidade e origem de satélite, inclusive quando o resultado é impedimento.
