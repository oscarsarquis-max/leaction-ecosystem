# SEGSENSE_UX_001 — Interface do SegSense no padrão Panne

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_UX_001 |
| Título | Arquitetura de informação e experiência inicial (padrão de interface Panne) |
| Categoria | UX — experiência e interfaces |
| Versão | 1.2 |
| Status | Vigente; identidade cromática em UX_002; fluxos em UX_003; marca perceptível no PRM_018 |
| Data | 14/09/2026 |
| Dependências | SEGSENSE_ARQ_001; SEGSENSE_ARQ_002; SEGSENSE_ADR_002; SEGSENSE_LNK_001; SEGSENSE_API_005; SEGSENSE_UX_002; SEGSENSE_UX_003; SEGSENSE_PRM_007; SEGSENSE_PRM_008 |
| Referência de padrão | Panne: ADR de interface, identidade visual, linguagem humana (R026-004), tela de acesso, tokens CSS |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 11/09/2026 | Especificação resumida: reutilizar o *projeto de interface* da Panne, sem copiar o produto Panne. |
| 1.1 | 11/09/2026 | Identidade SegSense: roxo, lilás e branco (UX_002). A referência a verde-escuro da v1.0 está superada. |
| 1.2 | 14/09/2026 | PRM_018: PNG oficial intacto; display usa recorte de margem transparente; tamanhos efetivos em UX_002. |

## 1. Decisão

O SegSense usará um **projeto de interface da mesma família da Panne**: React + TypeScript + Vite, shell horizontal, tokens CSS, linguagem humana, estados honestos e acessibilidade de base.

Isso **não** significa:

- copiar o produto de padaria (quadro, receitas, estoque, custos, Gigio);
- usar logos, paleta bege/grafite ou copy da Panne como marca SegSense;
- acoplar runtimes, bancos ou deploys;
- antecipar IdP, consentimento, Spider, Icatu ou cotação.

A Panne é **referência de padrão**. O SegSense permanece aplicação independente, com marca, domínio e jornadas próprias.

## 2. Para quem é este documento

Pode ser compartilhado com design, produto e implementação. Serve de briefing único até o PRM_008 (experiência pública) e o refinamento do admin.

## 3. Duas superfícies

| Superfície | Quem usa | Situação |
|---|---|---|
| **Admin** (`:5178`) | publicador / operador editorial | Já existe como fundação técnica; visual ainda raso |
| **Pública** (`/c/{token}`) | visitante do artigo / canal | **PRM_008** — ainda não existe; só há resolução JSON do link |

O visitante **não** vê o admin. O admin **não** é a jornada de seguros. As duas superfícies compartilham tokens, tipografia, estados e o logo oficial; diferem em densidade, navegação e o que pode ser dito.

## 4. O que se reaproveita da Panne

### 4.1 Stack e estrutura

- React + TypeScript + Vite (já no SegSense).
- CSS com **tokens nomeados** (não cores soltas na tela).
- Shell com cabeçalho compacto e **área útil máxima** no conteúdo.
- Navegação principal **horizontal**; sem menu lateral permanente no primeiro recorte.
- Router quando houver mais de uma rota real (admin já tem catálogo/oportunidade/links; público será rota própria).
- Frontend chama **somente o BFF** SegSense. Sem Spider, Icatu ou credencial no browser.

### 4.2 Linguagem humana

Herdar o princípio da Panne (R026-004), traduzido ao seguro contextual:

| Na superfície | Fora da superfície (ou recolhido) |
|---|---|
| Título da oportunidade, contexto editorial, CTA, validade, “link pausado / expirado / indisponível” | UUID, digest, `tokenHint`, `applicationId` cru, nomes de tabela, JSON, `CONTEXT_LINK_*` como jargão |
| “Tipo de risco: quebra de safra” | `fieldKey=riskType`, `source=PUBLISHER` |
| “Não foi possível continuar agora. Tente de novo em instantes.” | stack, SQL, 503 cru sem frase |

Detalhe técnico de auditoria, se existir no admin, fica recolhido. O visitante **não** vê auditoria.

Ocultar na UI **não** substitui autorização na API.

### 4.3 Estados obrigatórios

Toda tela (admin e pública) declara de forma visível:

- carregando;
- vazio (nada a mostrar, com próxima ação se houver);
- erro acionável (sem stack);
- backend indisponível (sem fingir sucesso);
- 401 no admin (autenticação ainda não configurada — frase humana);
- na pública: não encontrado, revogado, expirado, temporariamente indisponível.

Não inventar progresso de cotação, elegibilidade ou recomendação.

### 4.4 Acessibilidade e responsividade (mínimo)

- Landmarks, foco visível, `prefers-reduced-motion`.
- Contraste AA no par fundo/texto da marca SegSense.
- Alvos de toque ≥ 40 px no público e no admin em viewport estreita.
- Sem rolagem horizontal.
- Público: **mobile-first** (o artigo chega pelo celular). Admin: utilizável em desktop e tablet; mobile não é o piloto, mas não quebra.

## 5. O que é específico do SegSense

### 5.1 Marca

- Arquivo institucional **somente** `segsense/frontend/images/segsense logo.png` (SHA-256 `CEF4A9C0B8F7B0D8F2A50D85DE41FEA02498B15E3021EBB063E75945810C089D`). Não substituir, recolorir nem redesenhar.
- Display nas superfícies usa o derivado `frontend/images/segsense-logo-header.png`, recorte só da transparência periférica (PRM_018). Mesmo desenho, cores e proporção.
- Não usar logo da Panne nem da Icatu.
- Cabeçalho: altura da **marca visível** (não do quadro vazio). Admin: ~60 px + nome textual **SegSense**. Home/demonstrações: 68–100 px conforme viewport. Convite `/c/{token}`: 104–136 px.
- Paleta: **roxo, lilás e branco**, amostrada do logo oficial (detalhe em `SEGSENSE_UX_002`). Cores-base: violeta `#6018E8`, índigo `#1800B0`, lilás `#D9CCFF` / `#EAE3FF` / `#F5F2FF`, branco `#FFFFFF`, texto `#18151F`. **Não** importar bege/grafite da Panne nem o verde-escuro da fundação técnica (`#142017`) como identidade de marca. Tokens próprios (`--segsense-*`), copiando só a *mecânica* dos tokens da Panne. Cores semânticas (sucesso, atenção, erro, informação) nunca usam roxo.

### 5.2 Admin (evolução do que já existe)

Informação, não operação de seguros:

1. Catálogo (publicador, canal, ambiente).
2. Oportunidade e revisões.
3. Governança (submeter, aprovar, publicar, pausar, revogar).
4. Links contextuais: emitir (URL **uma vez**), listar sem segredo, revogar com justificativa.

Densidade de “quadro”: listas e detalhe, não Kanban. Confirmações destrutivas (revogar link) no mesmo espírito da Panne: diálogo claro, sem jargão.

Sem IdP: a UI continua dizendo que a autenticação não está configurada; não inventa login.

### 5.3 Pública (implementada no PRM_008)

Uma página intermediária, honesta, alimentada só pelo envelope já definido. Detalhe visual e fluxos: `SEGSENSE_UX_002`, `SEGSENSE_UX_003` e `SEGSENSE_UI_001`.

- `applicationId` interno, não como título de página;
- título da revisão; `callToActionLabel` só como finalidade textual;
- resumo contextual materializado só para apresentação (template + valores do publicador), como texto React;
- bindings não pessoais já vinculados;
- campos que o usuário ainda preencherá: só como definição, **sem coleta** neste recorte;
- validade efetiva;
- flags de cotação/elegibilidade/recomendação permanecem falsas e **não** viram selos de “análise feita”.

Estados da URL `/c/{token}`:

| Situação | O visitante lê |
|---|---|
| Token inválido / inexistente | Este endereço não está disponível. |
| Revogado | Este convite não vale mais. |
| Expirado | Este convite não está mais vigente. |
| Pausa / hierarquia / janela | Temporariamente indisponível. Tente mais tarde. |
| Oportunidade terminal | Este convite não está mais disponível. |

Sem formulário de dados pessoais, sem consentimento, sem fingerprint, sem cookie de rastreamento, sem sessão de usuário.

Continuidade: um único CTA local **Entender os próximos passos**. Sem fingir envio à seguradora.

## 6. Arquitetura de informação (resumo)

```text
Admin
  Início (saúde do BFF)
  Catálogo → Publicador → Canal → Ambiente
  Oportunidades → Detalhe → Governança
                              → Links (emitir / listar / revogar)

Público
  /c/{token} → contexto editorial mínimo → CTA
```

Não há, neste recorte: jornada de cotação, console Spider, preço, cobertura, produto recomendado.

## 7. Componentes a espelhar (sem copiar código da Panne)

Reimplementar no SegSense, com nomes e tokens próprios:

| Padrão Panne | Uso no SegSense |
|---|---|
| Shell + header | Admin e, em versão enxuta, público |
| Loading / empty / error | Todas as telas |
| Confirmação destrutiva | Revogar link; rejeitar publicação |
| `<details>` de auditoria | Só admin, se necessário |
| Tela de acesso em 3 colunas | **Fora** até existir IdP; não antecipar login público |

Não portar: assistente global, fluxo Gigio, quadro de produção, impressão de ficha de padaria, CMS editorial de login da Panne.

## 8. Fronteiras duras

- Browser → só BFF SegSense (`:8088` local).
- URL pública contém **apenas** token opaco; contexto fica no servidor.
- Token bruto: uma vez, no admin, no POST 201.
- Sem PII na UI pública deste recorte.
- Sem commit/push/deploy implícito neste briefing.

## 9. Critérios para aceitar uma tela

1. A pessoa entende o que fazer sem ler UUID, enum cru ou código HTTP.
2. O logo oficial não foi substituído.
3. Estados de ausência e falha são verdadeiros.
4. Admin e público não misturam papéis.
5. Nada simula seguro, Spider ou Icatu.
6. Mobile do público não exige zoom nem scroll horizontal.
7. Teste de regressão cobre a superfície (já é regra na Panne e no SegSense).

## 10. Fora de escopo deste documento

- PRM_009 (consentimento e coleta).
- IdP / tela `/entrar`.
- Identidade visual *verde* da Panne (ciclo Panne 028) aplicada ao SegSense.
- Alteração da Panne, do Hub ou da Spider.

## 11. Fontes (para quem for aprofundar)

No monorepo, somente leitura da Panne:

- `panne/documentacao/decisoes/ADR-INTERFACE-PANNE.md`
- `panne/documentacao/decisoes/IDENTIDADE-VISUAL.md`
- `panne/documentacao/decisoes/LINGUAGEM-HUMANA-E-DIVULGACAO-TECNICA.md`
- `panne/documentacao/produto/TELA-DE-ACESSO-024.md`
- `panne/frontend/src/styles/tokens.css`

No SegSense:

- logo: `frontend/images/segsense logo.png`
- contratos do link: `SEGSENSE_LNK_001`, `SEGSENSE_API_005`
- este arquivo: `documents/SEGSENSE_UX_001.md`
