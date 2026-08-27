# Linguagem humana e divulgação progressiva de detalhes técnicos

**Identificador:** R026-004
**Status:** decisão canônica de produto
**Âmbito:** toda a interface da Panne (não limitado a ordens)

## Princípio

A interface da Panne fala a **linguagem operacional** do usuário. Identificadores e detalhes de implementação só aparecem quando forem necessários para auditoria, suporte ou integração, dentro de uma área técnica **recolhida**, **explicada** e adequada ao perfil.

Ocultar na UI **não** substitui autorização na API. Não ampliar permissões para mostrar detalhes. Não expor segredos, tokens, credenciais ou URLs sensíveis.

## Público

| Perfil | Expectativa |
|---|---|
| Proprietário | Visão operacional clara; detalhes técnicos só sob demanda |
| Gestor de produção | Estado, próxima ação, quantidades legíveis |
| Técnico / formulador | Ciência e regulatório relevantes; **sem** UUIDs/hashes crus |
| Padeiro | Linguagem de chão de fábrica |
| Revisor regulatório | Termos científicos/normativos corretos; IDs só em auditoria |
| Comercial / compras | Códigos de negócio e nomes; sem infraestrutura |
| Leitor | Somente leitura operacional; mesma regra de divulgação |

Nenhum perfil recebe detalhes de implementação sem propósito.

## Taxonomia

### 1. Informação operacional principal

Visível e em linguagem humana: produto, receita, quantidade/unidade, estado, próxima ação, data/hora, responsável, estabelecimento, lote, fornecedor, preço/custo quando permitido, bloqueios e pendências.

### 2. Código público de negócio

Pode permanecer visível com rótulo e contexto: `ORD-…`, código de plano, lote, pedido, requisição, código de receita documentado. Preferir também o nome quando existir.

### 3. Detalhe técnico auditável

Recolhido por padrão em **Detalhes técnicos de auditoria**: hashes, UUIDs, IDs internos, versão de linha, idempotência, nomes de eventos internos, payloads, metadados de integração, diagnóstico.

### 4. Detalhe de implementação sem utilidade

Não aparece na UI: nomes de tabelas/classes/funções, stack traces, `null`/`undefined`, mensagens cruas de banco/framework, códigos internos sem ação possível.

## Exemplos

**Permitido (principal):**

- Integridade da ficha → Materiais: versão registrada
- Ordem criada / Pesagem iniciada
- `1.958,5 g` (apresentação operacional)
- `OP-2026-0001`

**Proibido (principal):**

- Hash SHA-256 aberto
- `order.created`, `batch.split`
- `1.958,456973 g` sem necessidade
- OIDC / PKCE / RLS / Bedrock / ledger / payload como jargão de tela
- UUID de produto como único rótulo da linha

## Divulgação progressiva

Componente: `TechnicalAuditDetails` (`frontend/src/components/TechnicalAuditDetails.tsx`).

Requisitos:

- recolhido por padrão (`<details>`);
- teclado e leitor de tela (estado expandido nativo);
- propósito curto;
- rótulos humanos;
- hash completo só na expansão;
- copiar só quando útil; sem cópia automática;
- atenção visual menor que a informação operacional;
- se não houver utilidade legítima → remover, não esconder.

## Precisão numérica

Política em `frontend/src/language/quantities.ts`:

| Contexto | Apresentação |
|---|---|
| Massa (g/kg) | até 1 casa decimal (pt-BR) |
| Unidades discretas | 0 casas |
| Demais | até 2 casas |
| Valor integral | só em detalhe técnico quando necessário |

Arredondamento é **somente visual**. Não altera valor persistido nem contabilidade.

## Acessibilidade

- Não depender só de cor.
- `<details>`/`<summary>` para expansão.
- Códigos públicos e nomes em texto legível.
- Erros: título humano + mensagem acionável; sem stack trace.

## Segurança

- Mesmo escopo de organização/permissão da entidade principal.
- Sem custos em perfis sem permissão.
- Sem tokens/credenciais/headers/URLs de banco na UI ou evidências.
- Isolamento entre organizações preservado.

## Checklist para novas telas

1. O que o usuário precisa fazer nesta tela?
2. Algum UUID/hash/evento interno está aberto?
3. Quantidades usam formatador operacional?
4. Códigos públicos têm rótulo e nome?
5. Detalhes técnicos estão no componente padrão?
6. Erros sem stack / `null` / JSON cru?
7. Teste de regressão cobre a superfície?

## Critérios de aceite (R026-004)

- Detalhe da ordem corrigido e **validado** (preservar).
- Cancelamento/substituição de consulta **não** é erro apresentável.
- Rotas principais auditadas; ocorrências corrigidas ou justificadas.
- Estoque/compras: precisão operacional e totais só por unidade homogênea.
- Dossiês: sem UUID truncado como nome; enums traduzidos; termos científicos preservados.
- Plano: nome/código do produto enriquecidos com RLS.
- Decisão e inventário documentados; R026-004 **validada integralmente** pelo Cortex.
- Testes impedem regressão de hashes/eventos/precisão/cancelamento.
- Rastreabilidade preservada (hashes disponíveis na expansão).
- Demo apresentável a interlocutor não técnico sem constrangimento por detalhes de implementação.

## Carregamento e cancelamento

- `ApiError("cancelado")` / `AbortError` não atualizam estado de erro.
- Respostas de geração anterior ou componente desmontado são ignoradas.
- Troca de organização continua abortando inflight no `ApiClient`.
- Preferir `useAsyncResource` ou `isCancelledError` em cargas.

## Implementação de referência

- `frontend/src/language/events.ts` — catálogo de eventos + fallback
- `frontend/src/language/quantities.ts` — quantidades
- `frontend/src/format.ts` — estados e rótulos
- `frontend/src/components/TechnicalAuditDetails.tsx`
- `frontend/src/human-language.test.tsx`
