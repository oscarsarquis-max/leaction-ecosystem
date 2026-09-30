# AF-ADR-001 — Produto independente no mesmo monorepo

## Controle

| Campo | Valor |
|---|---|
| Identificador | AF-ADR-001 |
| Versão | 0.2 |
| Status | PROPOSED |
| Data | 25/09/2026 |
| Dependências | ACTIONFINANCE_ARQ_001 §1.5 e §4 |

Decisão de negócio correlata (CONFIRMED_BY_OWNER): ActionFinance é aplicação independente no monorepo da Spider, sem Git aninhado.

## Contexto

Satélites do workspace (SegSense, SpiderBank) convivem no mesmo Git e conversam com a Spider por contrato. Compartilhar repositório costuma ser lido, por engano, como licença para importar código, banco ou runtime.

## Decisão

ActionFinance vive em `C:\Projetos\ActionFinance` no monorepo existente. Reutiliza convenções de pastas e disciplina documental. Não importa bibliotecas de `spider/backend`, Panne, SegSense ou Hub.

Isolamento permanente obrigatório: banco lógico próprio, schema próprio, usuário runtime exclusivo e acesso sem tabelas/FK/credenciais compartilhadas. No ambiente **local** da fundação, o volume (e o container, se houver) são dedicados.

Topologia física futura (mesmo cluster PostgreSQL hospedeiro versus instância separada) exige decisão própria. **Mesmo cluster não equivale a mesmas tabelas.** Deployment permanece independente.

## Alternativas rejeitadas

1. Repositório Git aninhado em `ActionFinance/`.
2. Módulo Maven da Spider ou dependência compile-time de entidades Spider.
3. Tabelas ou FK no banco/schema da Spider, Panne ou Hub.

## Consequências

- `git init` é proibido no diretório do produto.
- Adapter de integração usa DTOs locais do contrato publicado, não classes `br.com.banco.spider`.
- Fundação cria runtime próprio; este ADR não cria runtime.
