# ADR-012 — Foundation v1.0 e linha evolutiva Organization Intelligence (OI)

- Status: Aceito
- Data: 2026-08-17
- Responsáveis: arquitetura e produto QMind
- Afeta: documentação, roadmap, organização de módulos futuros
- Não altera: código executável, APIs, RLS, autenticação, Organization Profile, Guided Tour, Evolution Map, Assistant

## Contexto

O QMind consolidou um MVP operacional com jornada completa: autenticação, multi-tenancy, organizations, memberships, guided tour, audit plan, field central, evolution map, action items, assistente contextual, PDF e organization profile persistente (ICP-01).

Essa fundação é a primeira geração da plataforma. Ela continua em uso e evolução. Não será substituída nem descartada.

A próxima fase do produto exige compreender a organização (perfil, complexidade, dores, maturidade operacional, fit de jornada) e gerar inteligência para apoiar decisões — sem misturar essa responsabilidade com a operação diária de auditoria e evidências.

## Decisão

Adotar oficialmente **duas camadas arquiteturais**:

| Camada | Nome | Papel |
|--------|------|--------|
| **Foundation** | QMind Foundation **v1.0** | Operação: identidade, tenant, jornada de avaliação, evidências, planos, mapas, ações, relatórios |
| **OI** | QMind Organization Intelligence (**OI Alpha** / visão v2) | Compreensão organizacional e geração de insights; consome a Foundation; não substitui a Foundation |

A versão executável da plataforma permanece na linha Foundation. A OI é uma **linha evolutiva documental e de produto** nesta decisão; implementação ocorrerá em sprints posteriores, sempre aditiva.

## Motivação

1. Separar **operar** de **compreender**, evitando acoplar inteligência a fluxos críticos de isolamento e evidência.
2. Preservar ADR-001 (modular), ADR-002 (tenant), ADR-006 (auth) e ADR-008 (governança de IA) como invariantes da Foundation.
3. Permitir que Organization Context, Fit, recomendações e analytics cresçam sem regressão no MVP.

## Objetivos

- Foundation estável, versionada e documentada como baseline recuperável.
- OI com fronteira clara: lê/consome a Foundation; escreve insights/artefatos próprios; pode **sugerir** ações na Foundation, nunca embutir lógica OI dentro dos módulos Foundation.
- Dependência **unidirecional** no sentido de conhecimento de implementação:

```text
Foundation  →  OI  →  Insights  →  (opcionalmente) comandos/eventos na Foundation
```

A Foundation **nunca** importa, conhece ou depende da implementação interna da OI.

## Responsabilidades da Foundation

- Autenticação e autorização (Principal, memberships, papéis).
- Isolamento multiempresa (`X-Organization-Id`, RLS, tenant switch).
- Cadastro operacional de Organization e Membership.
- Organization Profile como **master data operacional** (ICP-01).
- Jornada: Guided Tour / Guided Assessment, Audit Plan, Field Central.
- Domínio de avaliação: assessments, interviews, evidence, findings, maturity packages, evolution map, action items, reports/PDF.
- Assistente contextual determinístico (sem LLM generativo obrigatório).
- Contratos OpenAPI e cliente `@qmind/api-client` da superfície operacional.

## Responsabilidades da OI

- Modelar e evoluir **Organization Intelligence** (contextos, perfis analíticos, fit, recomendações de jornada).
- Produzir insights, scores e recomendações a partir de dados autorizados da Foundation.
- Orquestrar consumo de Organization Profile e demais fatos org-scoped **via APIs/contratos públicos da Foundation**.
- Quando usar modelos generativos, subordinar-se ao ADR-008 (revisão humana, proveniência, sem bypass de RLS).
- Não possuir caminho alternativo de tenant; não enfraquecer RLS; não tornar-se fonte de verdade de evidências ou constatações.

## Limites entre as camadas

| Permitido | Proibido |
|-----------|----------|
| OI chama APIs Foundation com o mesmo OrgContext | Foundation importa pacotes/módulos OI |
| OI grava tabelas/artefatos próprios org-scoped | OI altera RLS, auth/deps, dual-engine |
| Foundation permanece funcional sem OI | OI escreve direto em `guided_sessions` / findings como dono |
| Insights sugerem action items / tour | OI aprova conformidade ou publica relatório sozinha |

## Benefícios

- Clareza para novos contribuidores: o que é “plataforma operacional” vs “inteligência”.
- Evolução incremental sem big-bang.
- Proteção do isolamento multiempresa e da rastreabilidade de evidências.
- Alinhamento com consultancy-led (ADR-011): a org continua dona dos dados; a OI interpreta, não expropria.

## Alternativas consideradas

### Fundir OI dentro dos módulos existentes

Rejeitado: misturaria inteligência com operação e aumentaria risco de regressão em tenant switch e guided JSONB.

### Substituir a Foundation por uma “plataforma OI”

Rejeitado: o MVP operacional é o ativo; a OI adiciona valor sobre ele.

### Microserviço OI imediato

Adiado: ADR-001 favorece monólito modular até fronteiras estáveis; OI pode nascer como módulo(s) irmão(s) e só depois se separar.

## Consequências

- Documentação de baseline e roadmap OI torna-se fonte oficial (`00_Architecture`, `04_Docs`).
- Próximas sprints de produto OI devem citar este ADR e respeitar a seta de dependência.
- Tags/marcos: Foundation **v1.0** (documental + baseline de código pós-ICP-01); OI **Alpha** (visão).
- Nenhuma mudança de comportamento nesta decisão.

## Referências

- Baseline: [`../00_Architecture/004_Foundation_Baseline_v1.md`](../00_Architecture/004_Foundation_Baseline_v1.md)
- Mapa de camadas: [`../00_Architecture/005_Foundation_OI_Layer_Map.md`](../00_Architecture/005_Foundation_OI_Layer_Map.md)
- Roadmap OI: [`../04_Docs/014_OI_Architectural_Roadmap.md`](../04_Docs/014_OI_Architectural_Roadmap.md)
- Evolução incremental: [`../04_Docs/015_Foundation_OI_Evolution_Strategy.md`](../04_Docs/015_Foundation_OI_Evolution_Strategy.md)
- ADR-001, ADR-002, ADR-006, ADR-008, ADR-011
- ICP-00 (descoberta Organization Context), ICP-01 (Organization Profile)
