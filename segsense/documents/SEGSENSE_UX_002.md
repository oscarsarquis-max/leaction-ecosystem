# SEGSENSE_UX_002 — Sistema visual e componentes de interface

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_UX_002 |
| Título | Sistema visual, tokens e componentes de interface |
| Categoria | UX — design system |
| Versão | 1.0 |
| Status | Aprovado e implementado no PRM_008 |
| Data | 11/09/2026 |
| Dependências | SEGSENSE_UX_001; SEGSENSE_LNK_001; SEGSENSE_API_005 |
| Decisão cromática | Roxo, lilás e branco |

## 1. Objetivo

Definir a identidade visual funcional do SegSense antes do PRM_008, eliminando decisões improvisadas na implementação.

Este documento especifica cores, tipografia, espaçamento, superfícies, componentes, estados, responsividade, acessibilidade e uso do logo para duas superfícies distintas:

- administração editorial;
- experiência pública contextual.

Não contém implementação, wireframes finais, autenticação, jornada de cotação ou integração externa.

## 2. Correção do UX_001

A referência a verde-escuro na seção 5.1 do `SEGSENSE_UX_001` está superada.

A identidade SegSense passa a usar:

- roxo como cor principal;
- lilás como superfície contextual e destaque suave;
- branco como fundo predominante;
- neutros escuros para leitura;
- cores semânticas reservadas para sucesso, atenção, erro e informação.

Não reutilizar a paleta bege/grafite da Panne. Da Panne são aproveitados apenas princípios estruturais: tokens nomeados, linguagem humana, shell eficiente, estados honestos e acessibilidade.

## 3. Origem da paleta

Amostragem técnica do logo oficial `frontend/images/segsense logo.png` identificou como cores dominantes aproximadas:

- violeta luminoso: `#6018E8`;
- índigo profundo: `#1800B0`;
- neutro escuro do lettering secundário: aproximadamente `#282820`.

As cores derivadas abaixo complementam o logo sem modificá-lo.

## 4. Tokens cromáticos

### 4.1 Marca

| Token | Valor | Uso |
|---|---:|---|
| `--segsense-purple-700` | `#1800B0` | ação principal pressionada, texto de marca forte |
| `--segsense-purple-600` | `#4610D4` | hover e elementos ativos |
| `--segsense-purple-500` | `#6018E8` | ação principal, foco, destaque de marca |
| `--segsense-purple-300` | `#A98BFF` | bordas e elementos ilustrativos |
| `--segsense-lilac-200` | `#D9CCFF` | seleção suave e destaque contextual |
| `--segsense-lilac-100` | `#EAE3FF` | cartões contextuais |
| `--segsense-lilac-050` | `#F5F2FF` | fundo elevado suave |
| `--segsense-white` | `#FFFFFF` | fundo principal e conteúdo |

### 4.2 Neutros

| Token | Valor | Uso |
|---|---:|---|
| `--segsense-ink-900` | `#18151F` | texto principal |
| `--segsense-ink-700` | `#3F3949` | texto secundário |
| `--segsense-ink-500` | `#6F687A` | metadado e ajuda |
| `--segsense-line-300` | `#D9D5E0` | divisória e borda |
| `--segsense-surface-100` | `#F7F6FA` | fundo administrativo |
| `--segsense-surface-000` | `#FFFFFF` | cartões e página pública |

Texto principal nunca usa lilás claro. Roxo sobre branco e branco sobre roxo devem ser validados em contraste AA antes da implementação. Para textos pequenos em fundo roxo, preferir `#1800B0` como fundo; `#6018E8` fica prioritariamente para controles, ícones e áreas de maior peso.

### 4.3 Semântica

| Token | Valor | Uso exclusivo |
|---|---:|---|
| `--segsense-success` | `#19724A` | ação concluída ou estado saudável |
| `--segsense-warning` | `#8A5700` | atenção ou expiração próxima |
| `--segsense-danger` | `#B42318` | erro, revogação ou ação destrutiva |
| `--segsense-info` | `#175CD3` | informação operacional neutra |

Não usar roxo para erro ou sucesso. Estado não pode depender apenas de cor: sempre combinar ícone, título e texto.

## 5. Tipografia

Não introduzir dependência externa de fonte nesta fase.

```text
Fonte principal: Inter, quando já empacotada localmente;
fallback: "Segoe UI", "Helvetica Neue", Arial, sans-serif.
```

Se Inter não estiver localmente disponível, usar diretamente a pilha de sistema. Não buscar fonte em CDN.

Escala:

| Papel | Tamanho/linha | Peso |
|---|---|---|
| Display público | `clamp(2rem, 5vw, 3.5rem)` / 1,08 | 700 |
| Título de página | `2rem` / 1,2 | 700 |
| Título de seção | `1.375rem` / 1,3 | 650–700 |
| Título de cartão | `1.0625rem` / 1,35 | 600 |
| Corpo | `1rem` / 1,55 | 400 |
| Corpo público | `1.125rem` / 1,6 | 400 |
| Metadado | `0.875rem` / 1,45 | 400–500 |
| Rótulo de campo | `0.875rem` / 1,4 | 600 |

Não usar caixa alta em frases. Caixa alta fica restrita a pequenos marcadores, com espaçamento entre letras e sem conteúdo essencial.

## 6. Espaçamento, forma e elevação

Escala base de 4 px:

```text
4, 8, 12, 16, 24, 32, 48, 64
```

Tokens principais:

| Token | Valor |
|---|---:|
| `--segsense-space-1` | `0.25rem` |
| `--segsense-space-2` | `0.5rem` |
| `--segsense-space-3` | `0.75rem` |
| `--segsense-space-4` | `1rem` |
| `--segsense-space-6` | `1.5rem` |
| `--segsense-space-8` | `2rem` |
| `--segsense-space-12` | `3rem` |
| `--segsense-space-16` | `4rem` |
| `--segsense-radius-control` | `0.625rem` |
| `--segsense-radius-card` | `1rem` |
| `--segsense-radius-dialog` | `1.25rem` |
| `--segsense-shadow-card` | `0 8px 24px rgba(24, 0, 176, 0.08)` |
| `--segsense-shadow-dialog` | `0 20px 56px rgba(24, 21, 31, 0.20)` |
| `--segsense-touch-target` | `2.75rem` |

Evitar excesso de cartões dentro de cartões. Divisórias e espaço em branco têm preferência sobre sombra.

## 7. Logo

Ativo único oficial:

```text
frontend/images/segsense logo.png
```

Regras:

- não redesenhar, recolorir, recortar permanentemente ou substituir;
- não criar símbolo derivado sem aprovação específica;
- preservar proporção e área de respiro;
- usar `object-fit: contain`;
- fornecer texto alternativo `SegSense` quando a imagem tiver função de marca;
- se o nome textual estiver adjacente e a imagem for redundante, usar `alt=""`;
- não usar a tagline como texto funcional da interface;
- conferir contraste do lettering secundário no fundo escolhido.

O arquivo é quadrado, com ampla margem interna. Por isso:

- no admin, usar em área reservada entre 56 e 72 px e acompanhar com o nome textual `SegSense`;
- na superfície pública, permitir apresentação entre 120 e 180 px conforme viewport;
- se o logo ficar ilegível em cabeçalho compacto, priorizar o nome textual e manter o ativo em tamanho honesto; não aplicar recorte CSS agressivo.

## 8. Shell administrativo

### 8.1 Estrutura

- Cabeçalho horizontal compacto e persistente apenas quando necessário.
- Logo + nome à esquerda.
- Navegação principal horizontal: `Início`, `Catálogo`, `Oportunidades`.
- Estado do ambiente e acesso à ajuda à direita, sem expor detalhes técnicos crus.
- Conteúdo com largura máxima aproximada de 1440 px e margens responsivas.
- Sem menu lateral permanente no primeiro recorte.

### 8.2 Hierarquia

```text
Cabeçalho
Breadcrumb humano
Título + descrição curta + ação principal
Estado/alerta contextual
Conteúdo principal em lista e detalhe
Detalhes técnicos recolhidos, quando legítimos
```

O admin é uma ferramenta editorial. Não deve parecer comparador, corretora, seguradora ou tela de cotação.

## 9. Superfície pública

A página `/c/{token}` será mobile-first, calma e focada.

Estrutura visual prevista:

```text
Marca SegSense
Contexto editorial
Título da oportunidade
Resumo humano
Valores contextuais já fornecidos pelo publicador
O que ainda será necessário, sem coletar nesta etapa
Validade e transparência
Um único CTA
Nota: nenhuma cotação ou recomendação foi realizada
```

Direção:

- fundo branco predominante;
- faixa ou halo lilás discreto para situar o contexto;
- título em tinta escura;
- CTA roxo sólido;
- nenhuma aparência de urgência artificial;
- nenhuma fotografia genérica de família, lavoura ou sinistro nesta fase;
- nenhum selo de “melhor opção”, “aprovado” ou “seguro garantido”.

O CTA do PRM_008 não pode fingir continuidade ainda inexistente. Sua ação e texto deverão ser definidos no wireflow UX_003.

## 10. Componentes-base

### 10.1 Ações

- `ButtonPrimary`: roxo sólido, texto branco.
- `ButtonSecondary`: branco, borda roxa, texto roxo profundo.
- `ButtonTertiary`: texto roxo, sem fundo permanente.
- `ButtonDanger`: vermelho semântico; nunca roxo.
- `IconButton`: rótulo acessível obrigatório.

Estados: default, hover, focus-visible, pressed, disabled e loading. Loading preserva largura do botão e não altera o verbo sem explicação.

### 10.2 Formulários

- rótulo sempre visível;
- ajuda abaixo do rótulo quando necessária;
- placeholder não substitui rótulo;
- borda neutra; foco com anel roxo de 2–3 px;
- erro junto ao campo e resumo no início do formulário quando houver múltiplos erros;
- campos ≥ 44 px no público e ≥ 40 px no admin;
- data e hora sempre indicam fuso ou conversão para UTC no admin.

### 10.3 Informação

- `StatusBadge`: cor + ícone + rótulo humano;
- `ContextSummary`: superfície lilás clara para contexto não pessoal;
- `Notice`: informação, atenção, sucesso ou erro;
- `EmptyState`: explica ausência e próxima ação;
- `LoadingState`: skeleton discreto ou texto, sem progresso inventado;
- `TechnicalAuditDetails`: `<details>` recolhido e exclusivo do admin;
- `Timeline`: eventos em ordem, nomes humanos e detalhes técnicos recolhidos;
- `DestructiveConfirmation`: título explícito, consequência, justificativa e botões com verbos completos.

### 10.4 Navegação

- `Breadcrumb`: nomes humanos, não UUIDs;
- `Tabs`: somente para visões irmãs do mesmo objeto;
- `Pagination`: próxima/anterior na UI; cursor permanece interno;
- nenhum link administrativo expõe token contextual bruto depois da emissão.

## 11. Estados de interface

### 11.1 Admin

| Estado técnico | Apresentação humana |
|---|---|
| Loading | “Carregando…” sem bloquear toda a tela quando desnecessário |
| Empty | Explicação da ausência + ação possível |
| 401 | “A autenticação administrativa ainda não está configurada.” |
| 403 | “Seu acesso não permite realizar esta ação.” |
| 404 | “Este item não foi encontrado neste contexto.” |
| 409 | “Os dados mudaram enquanto você trabalhava. Atualize e tente novamente.” |
| 422 | Regra de negócio explicada junto à ação |
| Backend indisponível | “O serviço está indisponível agora. Tente novamente em instantes.” |

### 11.2 Público

| Situação | Título | Ação |
|---|---|---|
| Carregando | “Preparando este convite…” | nenhuma |
| Não encontrado | “Este endereço não está disponível.” | voltar ao canal de origem, somente se destino seguro existir no futuro |
| Revogado | “Este convite não vale mais.” | nenhuma ação de continuidade |
| Expirado | “Este convite não está mais vigente.” | nenhuma ação de continuidade |
| Temporário | “Temporariamente indisponível.” | “Tentar novamente” |
| Terminal | “Este convite não está mais disponível.” | nenhuma ação de continuidade |
| Sucesso | título editorial real | um único CTA honesto |

Não mostrar códigos `CONTEXT_LINK_*`, status HTTP, stack, UUID ou JSON.

## 12. Responsividade

Breakpoints orientativos, não dependências rígidas:

- compacto: até 639 px;
- intermediário: 640–1023 px;
- amplo: 1024 px ou mais.

Público:

- conteúdo principal com largura de leitura entre 320 e 720 px;
- padding mínimo de 16 px no compacto;
- CTA em largura total no compacto;
- nenhum elemento exige hover;
- sem scroll horizontal a 320 px.

Admin:

- desktop prioriza lista + detalhe quando houver espaço;
- tablet empilha painéis preservando contexto;
- mobile não é o piloto, mas formulários e ações não podem quebrar;
- tabelas densas viram listas estruturadas quando não couberem.

## 13. Acessibilidade

- WCAG 2.2 AA como referência mínima;
- foco visível em todo controle;
- landmarks `header`, `nav`, `main` e `footer` quando aplicáveis;
- hierarquia única e lógica de headings;
- mensagens assíncronas com `aria-live` adequado;
- diálogo com foco inicial, contenção e devolução de foco;
- toque mínimo de 44 px na superfície pública;
- erro não depende apenas de cor;
- suporte a zoom de 200%;
- `prefers-reduced-motion` remove movimento não essencial;
- animações, se usadas, entre 120 e 200 ms e sem deslocamentos extensos;
- contraste deve ser medido em tokens reais, inclusive hover, disabled e foco.

## 14. Linguagem

Tom:

- claro;
- sóbrio;
- acolhedor sem informalidade excessiva;
- preciso sobre limites;
- sem medo, pressão ou promessa comercial.

Preferir:

- “contexto”; não `binding`;
- “convite”; não `token`;
- “vigente”; não `ACTIVE`;
- “pausado”; não `503`;
- “revisão aprovada”; não ID técnico aberto.

Não afirmar:

- “você está protegido”;
- “seguro aprovado”;
- “melhor seguro”;
- “cotação iniciada”, enquanto não houver cotação;
- “analisamos seu risco”, enquanto nenhuma análise tiver ocorrido.

## 15. Critérios de aceite do sistema visual

1. A tela é reconhecível como SegSense por roxo, lilás, branco e logo oficial.
2. Não se parece visualmente com a Panne, embora compartilhe disciplina estrutural.
3. Texto e controles atingem contraste AA.
4. Estado nunca depende apenas de cor.
5. Admin e público compartilham tokens, mas têm densidades distintas.
6. O logo permanece inalterado e legível.
7. Nenhuma tela expõe jargão técnico sem finalidade legítima.
8. Público funciona a 320 px sem scroll horizontal.
9. Estados de erro e indisponibilidade são honestos.
10. Nenhuma UI simula seguro, cotação, recomendação, Spider ou Icatu.

## 16. Próxima decisão

Após aprovação deste documento, produzir `SEGSENSE_UX_003` com:

- mapa de navegação do admin;
- fluxos de catálogo, oportunidade, governança e links;
- wireframes do admin;
- wireframes da página pública em sucesso e em todos os estados de falha;
- definição exata do CTA público do PRM_008;
- comportamento responsivo e de foco por fluxo.

Nenhum prompt de implementação deve ser emitido antes da aprovação do UX_003.
