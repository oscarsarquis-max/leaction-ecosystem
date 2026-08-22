# Limitações e backlog — governança regulatória

## O que este ciclo não é

Não é rótulo final, parecer jurídico, certificado, selo nem declaração automática de conformidade.

## Guardrail do Bedrock

Defesa adicional **pendente de identificador**. `BEDROCK_GUARDRAIL_ID` / `BEDROCK_GUARDRAIL_VERSION` existem no `.env.example` vazios. O `.env` real permanece ignorado. O Guardrail não é fonte de verdade.

## Evolução lexical

Não se ampliou a recuperação FTS neste ciclo. `plainto_tsquery` em português continua exigindo as palavras do objetivo no fragmento. Vocabulário controlado e sinônimos ficam no backlog. `grounding_insufficient` permanece falha fechada.

## RLS

Não foi implementado parcialmente. RLS continua obrigatório **antes** de abrir APIs de negócio.

## Ingestão futura de normas reais

Mapa para análise — metadados apenas, sem seed ativado e sem texto jurídico gerado por modelo:

- RDC 429/2020 e IN 75/2020
- RDC 727/2022
- Lei 10.674/2003
- RDC 843/2024 e IN 281/2024
- Portaria SVS/MS 326/1997
- RDC 275/2002
- RDC 216/2004
- NR-12 (Anexo VI) e NR-14
- normas estaduais e municipais
- normas técnicas privadas licenciadas

Se algum metadado for ingerido no futuro, permanece `draft` ou `pending_review`, com URL oficial, sem ativação automática.

AIR, consultas e minutas de BPF 2025–2026 são **propostas**, nunca obrigação vigente.

## IA

Claude não é chamado neste ciclo. No futuro poderá sugerir requisito candidato ou explicar achado, sempre `pending_review`, com citação revalidada localmente. Nenhuma resposta de IA é parecer ou confirmação de conformidade.
