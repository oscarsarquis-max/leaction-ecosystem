# CURSOR-007 — Implementar biblioteca de conhecimento e grounding

## Objetivo

Implemente a fundação versionada de conhecimento e recuperação da Panne para receitas, normas, documentos técnicos, fontes nutricionais, evidências e citações.

A recuperação será inicialmente determinística no PostgreSQL.

Não integre LLM, Claude, Bedrock ou embeddings neste ciclo.

## Princípio central

Toda informação recuperada deve preservar fonte, versão, data, vigência, jurisdição, localização no documento, integridade do conteúdo, estado de revisão e evidência utilizada.

Uma resposta futura de IA nunca será considerada fonte primária.

## Proteção do legado

Não acesse o MySQL legado. Não use credenciais ou dados da origem. Todas as operações ocorrerão exclusivamente no PostgreSQL local da Panne.

Confirme antes das migrações: PostgreSQL; banco lógico `panne`; ambiente local ou teste; head inicial `0005_nutrition_calculation`.

## Migração

Crie `0006_knowledge_grounding`.

Tabelas principais: `knowledge_source`, `knowledge_source_version`, `knowledge_fragment`, `knowledge_tag`, `knowledge_source_tag`, `grounding_query`, `grounding_result`, `grounding_citation`, `nutrition_expectation_profile`, `nutrition_expectation_profile_item`.

Faça também a evolução controlada necessária para representar limite de quantificação no dossiê nutricional do ingrediente.

## Requisitos

- Fontes com tipo, autoridade, jurisdição e isolamento organizacional.
- Versões imutáveis, hash, vigência explícita e estados regulatórios.
- Fragmentos citáveis com localizador, hash e FTS em português.
- Recuperação determinística fora de HTTP e LLM, com filtros normativos seguros.
- Citações reconstruíveis, append-only.
- Perfis de nutrientes esperados sem seed regulatório.
- LOQ modelado sem virar zero.
- Ingestão local controlada, sem crawler e sem endpoint público.
- Sem APIs além de `/health` e `/ready`. Sem frontend. Sem chat. Sem conformidade. Sem rótulo.

## Testes obrigatórios

PostgreSQL real e Python 3.12. Cobrir migração reversível, fontes, fragmentos, recuperação, perfis e LOQ.

## Restrições

Não acessar MySQL. Não integrar LLM/Bedrock/embeddings. Não criar chat, CRUD, crawler, seed regulatório não revisado, cópia integral indevida de receitas, commit, push, deploy ou CURSOR-008.

## Retorno obrigatório

Os 22 itens do contrato de execução, depois aguardar revisão do arquiteto.
