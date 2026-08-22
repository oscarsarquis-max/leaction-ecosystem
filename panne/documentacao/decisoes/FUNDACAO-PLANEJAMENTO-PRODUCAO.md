# ADR — Fundação de planejamento e ordens

Ciclo: CURSOR-012. Implementa o recorte persistente do chão de fábrica: plano, ordem, batelada, dependência, snapshot, liberação humana, evento append-only, permissões e RLS.

## Decisões

- A ordem é a fonte de verdade operacional. O plano agrupa o recorte; a batelada parte o alvo.
- Liberação é transação atômica, humana, com `production.order.release`. Sem IA.
- Formulação com aprovação válida e escala compatível são obrigatórias na liberação.
- Snapshots de materiais e etapas congelam nomes, unidades e quantidades; não dependem do cadastro vivo para leitura.
- Alteração material após liberação: cancelar com motivo e criar ordem substituta.
- Um papel por associação permanece. Padeiro não gerencia neste ciclo.
- `costing.read` não é criado nem concedido.
- Sem HTTP, frontend, pesagem real, consumo, estoque ou custo.

## Fora

Execução de etapa, rendimento real, emissão PDF/QR, relatórios materializados, offline, Bedrock, Cognito real.
