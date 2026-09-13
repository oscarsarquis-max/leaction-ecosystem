# SEGSENSE_PRM_008 — Sistema visual e experiência pública contextual

## Controle

- Projeto: SegSense
- Identificador: SEGSENSE_PRM_008
- Versão: 1.0
- Data: 11/09/2026
- Etapa anterior: SEGSENSE_PRM_007 e corretivo único aprovados
- Bases de UX: SEGSENSE_UX_001, SEGSENSE_UX_002 e SEGSENSE_UX_003

## Prompt para o Cursor

Implemente o `SEGSENSE_PRM_008` em `C:\Projetos\segsense`, no monorepo `leaction-ecosystem`.

Antes de alterar código, leia integralmente todos os documentos vigentes do SegSense, especialmente `SEGSENSE_UX_001`, os documentos `SEGSENSE_UX_002` e `SEGSENSE_UX_003` fornecidos com este prompt, `SEGSENSE_LNK_001`, `SEGSENSE_API_005`, `SEGSENSE_SEC_002`, `SEGSENSE_REV_007`, `SEGSENSE_PRM_007_COR_001` e migrations V1–V8. Leia apenas como referência estrutural os documentos da Panne citados em UX_001; não copie produto, código, componentes, marca ou paleta.

O SegSense é independente da Spider. Não altere Spider, Panne, `.cursor/` ou qualquer caminho fora de `segsense/`. Não faça commit, push ou deploy.

## 1. Objetivo

Implementar o sistema visual aprovado e duas superfícies coerentes:

1. refinamento do admin editorial existente;
2. página pública mobile-first `/c/{token}`.

A página pública consome somente o endpoint real:

```text
GET /api/v1/public/context-links/{opaqueToken}
```

Ela apresenta o contexto editorial não pessoal já associado ao link e explica os limites da etapa. Não coleta dados, não registra consentimento, não materializa objetivo e não chama Spider, Icatu ou mock.

## 2. Incorporação documental obrigatória

Instale integralmente em `documents/`:

- `SEGSENSE_UX_002.md` — sistema visual e componentes;
- `SEGSENSE_UX_003.md` — fluxos e wireframes.

Atualize `SEGSENSE_UX_001` para substituir a referência superada a verde-escuro pela decisão roxo/lilás/branco. Preserve histórico e aumente sua versão.

Inclua UX_002 e UX_003 no índice oficial e registre versões, situação e dependências. Crie cópia integral deste prompt em `documents/SEGSENSE_PRM_008.md`.

## 3. Identidade visual

Implemente tokens CSS próprios `--segsense-*` conforme UX_002.

Cores-base:

- violeta `#6018E8`;
- índigo profundo `#1800B0`;
- lilás `#D9CCFF`, `#EAE3FF` e `#F5F2FF`;
- branco `#FFFFFF`;
- texto `#18151F`;
- neutros e cores semânticas definidos em UX_002.

Não importar bege/grafite da Panne. Não usar roxo para erro, alerta ou sucesso. Estado nunca depende somente de cor.

Use fonte de sistema; não carregar fonte por CDN. Implemente espaçamento, raios, sombras, foco e `prefers-reduced-motion` pelos tokens documentados.

## 4. Logo oficial

Use exclusivamente:

```text
frontend/images/segsense logo.png
```

Não modificar, recortar permanentemente, recolorir, substituir ou criar nova versão. Registre SHA-256 antes e depois.

Como o arquivo é quadrado e possui margem interna:

- admin: área de 56–72 px acompanhada do nome textual `SegSense`;
- público: apresentação de 120–180 px;
- `object-fit: contain`;
- texto alternativo ou `alt=""` conforme redundância;
- não usar tagline como instrução da interface.

## 5. Estrutura do frontend

Adote roteamento React real, com navegação direta e refresh funcionando:

```text
/admin
/admin/catalogo
/admin/oportunidades
/admin/oportunidades/:opportunityId
/c/:token
```

Se o projeto ainda não possuir router, adicione dependência estável compatível com React 19 e documente a decisão. Não invente autenticação.

Separe claramente:

- shell administrativo;
- layout público;
- tokens e componentes compartilháveis;
- tradução de erros técnicos para mensagens humanas;
- cliente da API pública sem credenciais.

Frontend chama somente o BFF SegSense.

## 6. Refinamento do admin

Implemente o padrão de UX_003:

- cabeçalho horizontal compacto;
- logo e nome;
- navegação `Início`, `Catálogo`, `Oportunidades`;
- breadcrumb humano;
- conteúdo com largura máxima e margens responsivas;
- catálogo coordenado por Publicador → Canal → Ambiente;
- detalhe de oportunidade com abas acessíveis:
  - Conteúdo;
  - Governança;
  - Links contextuais;
- linguagem humana para estados e ações;
- detalhes técnicos somente em `<details>` recolhido quando úteis;
- diálogos acessíveis para ações destrutivas;
- emissão de link em revisão clara antes da confirmação;
- URL exibida integralmente somente após o POST 201;
- copiar endereço com confirmação por `aria-live`;
- depois de fechar a confirmação, nunca recuperar ou reconstruir o token.

Não inventar busca, filtro ou paginação visual sem suporte real da API.

Sem IdP, o admin deve continuar exibindo honestamente que a autenticação administrativa não está configurada. Não criar tela de login.

## 7. Página pública `/c/{token}`

Crie uma página mobile-first independente do shell administrativo.

Fluxo:

1. extrair o token apenas da rota;
2. validar tamanho/formato básico sem exibi-lo;
3. consultar o BFF;
4. apresentar sucesso ou estado humano correspondente;
5. não persistir token em storage, cookie, analytics ou estado global duradouro;
6. abortar request ao desmontar e ignorar resposta obsoleta.

No sucesso, apresentar:

- logo SegSense;
- marcador “Um convite contextual”;
- título editorial;
- resumo humano, sem expor template cru;
- valores do publicador com rótulos humanos;
- informações adicionais que poderão ser necessárias, apenas como definição;
- validade em português do Brasil;
- transparência;
- afirmação de que nenhuma cotação, elegibilidade ou recomendação foi realizada.

Não mostrar `applicationId`, token, IDs, field keys, enums crus, JSON, objective template ou detalhes de auditoria.

## 8. Renderização segura do resumo

O envelope fornece template e `publisherValues`. Materialize somente para apresentação do resumo contextual, no frontend, sob estas regras:

- substituir apenas placeholders declarados que possuam valor do publicador;
- renderizar exclusivamente como texto React, nunca HTML;
- nunca usar `dangerouslySetInnerHTML`;
- placeholders sem valor devem produzir frase humana ou ser omitidos sem deixar `{{campo}}` visível;
- não materializar `objectiveTemplate`;
- não persistir o resultado;
- testes devem cobrir conteúdo hostil como texto inerte.

Se não for possível produzir frase gramaticalmente segura com placeholder ausente, exiba o resumo estático e os valores contextuais separadamente. Não invente texto.

## 9. CTA temporário aprovado

O botão principal desta etapa será:

```text
Entender os próximos passos
```

Ele executa somente ação local:

- abre ou conduz à seção “O que acontece agora?”;
- explica que nenhuma informação pessoal foi coletada;
- explica que nenhuma seguradora recebeu informações;
- informa que nenhuma cotação ou recomendação ocorreu;
- informa que a continuidade ainda não está disponível.

O botão não cria ContextInstance, não chama API de negócio, não coleta dados e não registra consentimento.

O `callToActionLabel` vindo da revisão não deve ser transformado em botão ativo. Mostre-o, quando apropriado, apenas como finalidade textual e neutralize linguagem enganosa. Não exiba chamadas como “Contratar agora” como ação funcional.

## 10. Estados públicos

Mapeie sem expor códigos técnicos:

| API | Interface |
|---|---|
| carregando | “Preparando este convite…” |
| 404 | “Este endereço não está disponível.” |
| 410 revogado | “Este convite não vale mais.” |
| 410 expirado | “Este convite não está mais vigente.” |
| 410 terminal | “Este convite não está mais disponível.” |
| 503 | “Temporariamente indisponível. Tente novamente em instantes.” |
| falha de rede/backend | mensagem temporária sem fingir estado terminal |

Somente 503/falha temporária oferece `Tentar novamente`. Estados terminais não oferecem continuidade impossível.

Não criar retorno para origem, pois ainda não existe URL de retorno segura contratada.

## 11. Acessibilidade

Atender UX_002/003 e, no mínimo:

- landmarks e heading único;
- navegação e abas por teclado;
- foco visível;
- alvos públicos ≥44 px;
- contraste WCAG 2.2 AA medido;
- zoom 200%;
- 320 px sem scroll horizontal;
- `aria-live` para carregamento, retry e cópia;
- diálogos com contenção e devolução de foco;
- foco no conteúdo principal após mudança de rota;
- motion reduzido;
- nenhuma informação transmitida apenas por cor ou ícone.

## 12. Segurança e privacidade

- Não registrar nem exibir o token.
- Não usar localStorage, sessionStorage ou cookie na rota pública.
- Não adicionar analytics, fingerprint, pixel ou fonte externa.
- Não alterar CORS do backend.
- Não criar proxy que logue a URL pública completa.
- Não introduzir `dangerouslySetInnerHTML`.
- Não inserir dados pessoais em exemplos, fixtures ou screenshots.
- Não ampliar endpoints públicos.
- Não modificar o contrato seguro do PRM_007 sem necessidade comprovada.

## 13. Componentes mínimos

Implemente componentes próprios, sem copiar código da Panne:

- `SegSenseLogo`;
- `AdminShell`;
- `PublicShell`;
- `HumanStatus`;
- `AsyncState`;
- `ContextSummary`;
- `TechnicalAuditDetails` somente admin;
- `DestructiveConfirmation`;
- `CopyOnceLink`;
- `OpportunityTabs`;
- `PublicTransparency`.

Evite abstrações genéricas prematuras. Componentes devem existir porque são usados por mais de uma tela ou encapsulam comportamento crítico.

## 14. Testes obrigatórios

### Frontend

- roteamento admin e público, inclusive refresh/fallback do Vite;
- token não aparece em texto, logs instrumentados, storage ou links internos;
- sucesso público com bindings e campos ainda necessários;
- template renderizado como texto seguro;
- placeholder ausente não aparece cru;
- objective template e IDs não aparecem;
- CTA abre somente transparência local e não faz request de negócio;
- 404, revogado, expirado, terminal, 503 e erro de rede;
- retry apenas em estado temporário;
- request abortado e resposta obsoleta ignorada;
- emissão e cópia única no admin;
- fechamento elimina token bruto do estado acessível;
- abas, diálogo, foco e `aria-live`;
- 320 px sem regressão estrutural verificável;
- ausência de `dangerouslySetInnerHTML`, storage, cookie, analytics e chamadas externas;
- logo importado do arquivo oficial;
- traduções sem enums/códigos técnicos visíveis;
- regressões completas.

### Backend/regressão

- `mvnw verify` completo;
- endpoint de resolução e headers inalterados;
- V1–V8 validadas;
- nenhuma migration nova, salvo necessidade técnica inevitável e previamente justificada — a expectativa é zero migration;
- nenhuma alteração de contrato sem justificativa e teste.

### Verificação visual

Use browser real para validar:

- admin em 1440×900 e 768×1024;
- público em 1440×900, 390×844 e 320×568;
- sucesso e todos os estados públicos;
- foco por teclado;
- ausência de scroll horizontal;
- contraste dos tokens;
- logo sem distorção.

Anexe screenshots ou caminhos de evidência sem incluir token real. Use fixture somente em teste automatizado; runtime continua usando API real e estados honestos.

## 15. Documentação

Crie:

- `SEGSENSE_UI_001.md` — arquitetura implementada do frontend, rotas e componentes;
- `SEGSENSE_REV_008.md` — evidências funcionais, visuais, acessibilidade, segurança e SAT;
- `SEGSENSE_PRM_008.md` — cópia integral deste prompt.

Atualize UX_001, índice, PLN_001, README e documentos afetados. Marque UX_002 e UX_003 como aprovados e implementados apenas se todos os critérios forem atendidos.

## 16. Validação final

Execute:

- frontend `npm ci`, lint, testes e build;
- backend `mvnw.cmd verify`;
- Compose sem apagar volume;
- backend `:8088`, frontend `:5178`, PostgreSQL `:5437`;
- HTTP público e administrativo real;
- inspeção de bundle e source por token, storage, analytics, HTML inseguro e chamadas externas;
- inspeção do Git e alterações externas;
- hash do logo antes/depois.

Se reiniciar processos, devolva o ambiente funcional.

## 17. Critérios de aceite

- identidade roxo/lilás/branco consistente;
- admin refinado sem perder funcionalidades existentes;
- `/c/{token}` funcional e mobile-first;
- estados públicos humanos e corretos;
- CTA exclusivamente local e honesto;
- nenhuma coleta, consentimento ou integração simulada;
- token protegido no browser;
- contraste, teclado, foco e responsividade validados;
- UX_002/003 instalados e indexados;
- logo byte a byte preservado;
- todos os testes e builds aprovados;
- nenhuma alteração fora de `segsense/`.

## 18. Devolutiva obrigatória

Apresente:

1. documentos UX instalados e correção do UX_001;
2. arquivos criados/alterados;
3. tokens e identidade visual;
4. rotas e arquitetura do frontend;
5. refinamento do admin;
6. página pública e renderização do contexto;
7. CTA e transparência;
8. estados públicos;
9. acessibilidade e responsividade;
10. proteção do token e inspeção de privacidade;
11. testes, builds, browser e evidências visuais;
12. ambiente e HTTP real;
13. hash do logo;
14. SAT-01 a SAT-10;
15. Git e alterações externas;
16. ausências confirmadas.

Não faça commit, push ou deploy.
