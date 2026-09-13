# SEGSENSE_ARQ_003 — Fronteira preparada SegSense–Spider (sem conexão operacional)

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_ARQ_003 |
| Título | Fronteira do satélite sem contrato externo executável |
| Categoria | ARQ — Arquitetura |
| Versão | 1.0 |
| Status | Preparado documentalmente; implementação bloqueada |
| Data | 12/09/2026 |
| Dependências | SEGSENSE_INT_001; SEGSENSE_ADR_003; SEGSENSE_ARQ_002 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 12/09/2026 | Ramo B: fronteira local completa; sem seta operacional para a Spider. |

## 1. O que existe hoje

O SegSense opera ponta a ponta **dentro de si**: catálogo, oportunidade, governança, link, aviso, instância, autorização e retirada. O browser chama somente o BFF. O BFF não chama a Spider.

## 2. Diagrama (sem conexão operacional)

```text
Browser
  └── React (segsense-frontend)
        └── HTTP local apenas
              └── Satellite BFF (segsense-backend)
                    └── Postgres local (:5437)

Spider (aplicação independente)
  [Satellite Contract externo: AUSENTE]
  [nenhuma seta, client, fila ou callback nesta etapa]

Insurance Provider Mock (aplicação independente futura)
  [fora desta etapa; PRM_012/013]
```

Não há linha de integração. Uma linha aqui seria falsa.

## 3. O que a autorização local significa

`ContextInstance` `AUTHORIZED` autoriza o **uso das informações no SegSense**, na finalidade versionada do aviso. Não é submissão de objetivo, preview, Execution Plan nem envio a seguradora.

A UI pública encerra nessa fronteira. Não há CTA de preview, confirmação, envio ou resultado Spider.

## 4. Dois textos ARCH-017

| Artefato | Onde | Status |
|---|---|---|
| Cópia SegSense | `documents/references/SPIDER-ARCH-017.md` | `PROPOSED / ARCHITECTURAL BASELINE` — não substituída nem editada neste PRM |
| Texto vigente na Spider | `spider/docs/architecture/SPIDER-ARCH-017-satellite-architecture.md` (commit `4ba112d`, 2026-09-09) | Ideal **não implementado**; Contextual Link e SpiderBank ≠ Satellite Contract |

São artefatos distintos. A cópia PROPOSED **não** foi aceita pela Spider.

## 5. Icatu (planejamento, não implementação)

Uma futura seção comercial dedicada à Icatu Seguros deverá identificar claramente a simulação. A integração inicial, quando houver, será mockada a partir de informações públicas verificadas no portal de APIs da Icatu, por **aplicação independente**, jamais incorporada ao SegSense ou à Spider. PRM_012/013 permanecem responsáveis. Este documento não acessa o portal nem cria seção comercial.

## 6. Fora desta arquitetura

Client HTTP Spider/Icatu, credencial de satélite, mapper Satellite Contract, DTO homônimo, tabela de outbox, botão de continuidade, escolha de route/adapter/executor/Execution Plan.
