# Icatu integration (placeholder)

A Icatu é um **executor potencial** de capabilities que a Spider resolver. O SegSense, como Insurance Reference Satellite, **não escolhe** e **não implementa** integração operacional direta com a Icatu.

Um Insurance Provider Mock futuro, se existir, será **aplicação independente** (runtime, configuração, endpoints e ciclo de vida próprios). Não será módulo interno da Spider nem do SegSense. Este diretório permanece só documentação de limite.

O backend Java exercerá a função de Satellite BFF. Chamadas de plataforma passam pelo BFF e, quando existirem, pelo Satellite Contract com a Spider. O frontend nunca conversa com a Icatu nem guarda credenciais técnicas.

## Boundary atual

```text
Runtime: SIMULATED_INFRASTRUCTURE
Integrações: MOCK_ONLY
```

Nenhuma integração real está sendo declarada. Não há client HTTP, adapter, sandbox, catálogo, payload ou credencial neste diretório. A pasta existe só para registrar o limite: executor de capability ≠ sistema do satélite.

Planejamento (não implementação desta etapa): uma futura seção comercial dedicada à Icatu Seguros deverá identificar claramente a simulação. O mock, quando houver, será aplicação independente (PRM_012/013), jamais incorporada ao SegSense ou à Spider.

## Regras

- não inventar endpoints, payloads, autenticação ou produtos;
- não tratar a Icatu como implementação interna do SegSense;
- não ligar oportunidade, jornada ou BFF a um endpoint da Icatu;
- capability permanece independente do sistema concreto que a executar;
- qualquer uso futuro da Icatu ocorre por resolução da Spider, com contrato e ambiente autorizados.
