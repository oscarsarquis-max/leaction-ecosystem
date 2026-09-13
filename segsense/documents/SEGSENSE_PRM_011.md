# SEGSENSE_PRM_011 — Âncora visual comercial e backoffice de demonstrações

## Controle

- Projeto: SegSense
- Identificador: SEGSENSE_PRM_011
- Versão: 1.0
- Data: 12/09/2026
- Etapa anterior: `SEGSENSE_PRM_010` aprovada com ressalva visual
- Mudança de sequência: o antigo PRM_011 de integração Spider fica **adiado**, não concluído nem renumerado silenciosamente
- Execução: Cursor, somente `C:\Projetos\segsense`

## Prompt para o Cursor

Implemente esta etapa exclusivamente em `C:\Projetos\segsense`, no monorepo `leaction-ecosystem`. O objetivo é produzir uma **âncora visual convincente para apresentação do SegSense** e, simultaneamente, avançar o **backoffice editorial** que governa demonstrações. Não implemente integração Spider, Icatu nem provider mock neste PRM.

Antes de alterar arquivos, leia integralmente os documentos vigentes, em especial `SEGSENSE_ARQ_001/002/003`, `SEGSENSE_ADR_001/003`, `SEGSENSE_INT_001`, `SEGSENSE_REQ_002`, `SEGSENSE_PLN_001`, `SEGSENSE_UX_001/002/003`, `SEGSENSE_UI_001`, `SEGSENSE_FUN_002`, `SEGSENSE_API_001/006`, `SEGSENSE_SEC_001/003`, `SEGSENSE_REV_010` e V1–V11. Inspecione o frontend/admin existentes para reutilizar tokens, shell, autenticação deny-by-default, correlação, erros, foco e padrões de governança. Não copie a Panne nem modifique Spider.

## 1. Fatos externos e limites da referência Icatu

Fontes públicas iniciais a **verificar por navegação normal**, sem scraping, autenticação, contorno de barreira ou criação de conta:

- `https://portal-api.icatuseguros.com.br/` — apresentação pública do Hub de APIs;
- `https://portal-api.icatuseguros.com.br/apis` — catálogo público;
- `https://portal-api.icatuseguros.com.br/terms-of-use` — termos públicos.

Na verificação preliminar de 12/09/2026, a página pública do catálogo **não expôs especificações de operações sem autenticação**. Isso não prova ausência de APIs; prova somente que não há contrato detalhado disponível para este trabalho sem acesso autorizado. O portal apresenta o Hub como meio de integrar soluções e informa que suas APIs são autenticadas. Os termos vinculam acesso/uso a cadastro aprovado e relação contratual. Não trate marketing do portal como concessão de licença, parceria, sandbox ou autorização de uso da marca.

Crie `SEGSENSE_SRC_001.md` com URL direta, data de consulta, trecho factual resumido em paráfrase, acesso público versus restrito, status de verificação e implicação para o conteúdo. Se uma fonte não abrir, marque `NÃO VERIFICADO`; não preencha lacunas. **Não** copiar conteúdo extenso, logos, imagens, marcas gráficas ou especificações não públicas da Icatu.

## 2. Correção herdada do PRM_010

O fluxo público de sucesso do PRM_009 segue sem inspeção visual ponta a ponta, por ausência de IdP no runtime. Nesta etapa, planeje e execute uma prova visual isolada com dados sintéticos estritamente NON_PERSONAL e fixture administrativa **somente de teste**; não crie login fictício, bypass no perfil `local`, token permanente, seed privilegiado ou mock de produção.

Verifique em browser real, se disponível: `/c/{token}` com notice aprovado, campos BOOLEAN/DATE/NUMBER/ENUM, revisão, autorização e retirada; público em 1440×900, 390×844 e 320×568; admin em 1440×900 e 768×1024; zoom 200%; teclado, foco, estados de erro e ausência de rolagem horizontal. **Nunca** grave token bruto ou credencial em screenshot, console ou documento. Se o browser não estiver disponível, declare a lacuna e apresente testes de componente/HTTP sem alegar validação visual.

## 3. Decisão de produto e linguagem

A página dedicada será intitulada, de modo inequívoco:

```text
SegSense + Icatu Seguros — cenário demonstrativo não oficial
```

Ela existe para apresentar **uma possibilidade comercial e arquitetural**, não uma integração operacional nem parceria firmada. A Icatu é **provedora potencial de um cenário futuro**, não executor selecionado, cliente, patrocinador ou parceira certificada. Use o nome textual apenas para identificar o cenário; não use logo, cores institucionais, fotografias, selo, assinatura visual ou texto que sugira endosso da Icatu.

Em posição visível acima da primeira dobra e junto a qualquer ação, exiba:

```text
Demonstração conceitual. Não é uma oferta de seguro, integração oficial ou serviço da Icatu.
```

Não afirmar que há contrato, credenciais, sandbox, produto compatível, cobertura, preço, cotação, elegibilidade, contratação, emissão, atendimento ou dados transmitidos. Não usar “comprar”, “contratar agora”, “simular seu seguro” ou urgência artificial. A seção de prova técnica deve distinguir `OPERANTE NO SEGSENSE`, `PLANEJADO / DEPENDE DA SPIDER` e `FUTURO MOCK INDEPENDENTE`; não usar um único indicador genérico “integrado”.

## 4. Âncora visual pública imediata

Crie uma rota pública **sem token** e sem coleta:

```text
/demonstracao/icatu
```

Esta rota deve estar acessível no ambiente local mesmo antes de qualquer registro administrativo ser aprovado. Sua camada base é **narrativa institucional do SegSense controlada em código**, sem afirmações de produto Icatu; não depende de seed publicado nem de login. Ela não pode consultar Spider, Icatu ou mock, nem criar ContextInstance. Use exclusivamente o BFF SegSense se precisar de estado operacional local; não transforme disponibilidade do BFF em status de integração.

Direção visual: roxo/lilás/branco, logo oficial SegSense, composição editorial premium e legível, sem “dashboard” artificial. Estrutura mínima:

1. **Hero** — “Do contexto à oportunidade de proteção”, subtítulo humano; marcador de cenário demonstrativo não oficial; CTA “Explorar como funcionaria” que navega apenas na própria página.
2. **Ponto de origem** — um artigo digital ilustrativo genérico (por exemplo risco agrícola), com aviso explícito de que é texto fictício e **não** prova de produto/cobertura da Icatu. Link ilustrativo não cria sessão nem promete contratação.
3. **Mecanismo SegSense hoje** — publicador → oportunidade aprovada → link contextual → convite público → finalidade/manifestação local. Cada passo deve corresponder a capacidade realmente implementada.
4. **Fronteira Spider** — objetivo + contexto poderiam seguir ao Satellite Contract no futuro; marcar como bloqueado pela ausência do contrato externo executável (`SEGSENSE_ADR_003`). Não desenhar seta como fluxo já ativo.
5. **Fronteira do provedor** — futuro Insurance Provider Mock como aplicação independente, baseado em informações públicas verificadas e claramente não oficial. A Icatu real não recebeu dados e não foi chamada.
6. **O que um piloto precisaria comprovar** — contrato Spider, catálogo de API autorizado, instrumento comercial/regulatório, homologação, segurança e textos jurídicos; não converter pendência em vantagem já entregue.
7. **Explorar a plataforma** — links apenas para rotas SegSense existentes que façam sentido e sejam honestas. Admin continua 401 sem IdP; não enviar visitante a um beco de login inexistente.

Use uma visualização pequena e útil do fluxo (HTML/CSS/SVG próprio, acessível) somente onde a relação entre as fronteiras ficar mais clara. Não gerar imagem falsa de apólice, tela oficial ou contrato. Não usar componentes ou imagens da Panne.

O estado de exemplo não precisa fingir API: animações/abas podem revelar explicações locais, desde que rotuladas como **ilustração**, sem POST de negócio, valores pessoais, tracking ou timers que pareçam execução. Permita navegar por teclado; respeite `prefers-reduced-motion`.

## 5. Backoffice de apresentações demonstrativas

Crie no SegSense um módulo **editorial**, não de integração, para governar versões futuras do conteúdo específico de cenários de apresentação. Nome conceitual: `DemonstrationStory`. Não invente entidade `IcatuProduct`, adapter, route ou provider contract.

Escopo mínimo:

- identificador estável (`key`, como `icatu-demonstracao`), título, resumo, público pretendido, nota de escopo, blocos narrativos ordenados e lista de referências públicas;
- cada alegação factual sobre terceiro vinculada a uma referência verificada de `SEGSENSE_SRC_001`, com data e status;
- campos de conteúdo somente textual e não pessoal; sem HTML arbitrário, script, iframe, URL de execução, imagem externa ou markup do terceiro;
- versão/snapshot imutável, revisão editorial, aprovação com ator, justificativa e timestamp UTC;
- estados `DRAFT`, `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, `PAUSED`, `RETIRED` com transições explícitas;
- `PUBLISHED` significa publicação **apenas do conteúdo demonstrativo** na rota SegSense, nunca ativação de API ou seguradora;
- mudanças posteriores geram nova revisão e exigem nova aprovação; revisão histórica nunca muda;
- revisão/pausa/retirada auditáveis e sem exclusão destrutiva;
- versões não aprovadas nunca aparecem publicamente.

Crie endpoints admin sob `/api/v1/admin/demonstrations` com authorities próprias (`read`, `write`, `approve`, `publish`), deny-by-default, 401 anônimo e 403 em fixture autenticada sem autoridade. O fluxo administrativo deve ter listagem, edição, histórico, revisão de alegações/fontes, aprovação, publicação/pausa/retirada e preview **administrativo** claramente marcado. Não invente IdP, usuário de runtime nem client externo.

Crie `GET /api/v1/public/demonstrations/icatu-demonstracao` **somente** para snapshot PUBLISHED, sem PII, IDs internos, autores ou detalhes técnicos. Se não houver conteúdo publicado, retorne estado claro de ausência; a página `/demonstracao/icatu` continua exibindo sua narrativa institucional base, sem fingir que há uma história administrada publicada. Proíba cache inadequado de versão retirada e trate 404/503 honestamente.

No PostgreSQL, use V12+ incremental, preserve V1–V11 e o volume atual. FKs/constraints devem impor versão, estado, referência de fonte, escopo e imutabilidade de snapshot; testes SQL diretos para cross-revision, inserção após aprovação, alteração de conteúdo histórico e publicação sem decisão devem falhar. Evite trigger frágil dependente de ordem de flush sem teste de transação real. Se um desenho mais simples cumprir as invariantes, prefira-o.

## 6. Ligação entre âncora e backoffice

A rota pública pode incorporar blocos administrados **somente quando houver snapshot PUBLISHED**. A camada base permanece intacta e deve continuar clara sem backend. Conteúdo administrado entra em seção identificada, por exemplo “Cenário editorial publicado”, com versão/data e origem das alegações em links externos seguros (`rel="noopener noreferrer"`), sem transformar a página em agregador de APIs.

Uma falha do endpoint editorial não deve trocar o cenário por conteúdo inventado nem mostrar “integração indisponível”. Mostre “Conteúdo editorial adicional indisponível” se necessário. Em nenhuma circunstância o conteúdo admin pode remover os avisos de não oficialidade, alterar rótulos de fronteira ou criar CTA de contratação.

## 7. UX e acessibilidade

- Seguir `SEGSENSE_UX_002/003` e tokens existentes, sem paleta Icatu.
- Hero e narrativa claramente distintos do admin e da página `/c/{token}`.
- Linguagem humana e evidência visível, sem jargão no primeiro nível.
- Navegação por teclado, foco previsível, landmarks, heading único, contraste AA, alvos ≥44 px, zoom 200%, 320 px sem scroll horizontal.
- Estados de carregamento/ausência/indisponibilidade honestos.
- Texto alternativo correto no logo oficial; SHA-256 byte a byte inalterado.
- Nenhum token/contexto de usuário em URL de demonstração.
- Não usar analytics, cookies, localStorage/sessionStorage, fingerprint, font/CDN externos ou `dangerouslySetInnerHTML`.

## 8. Testes obrigatórios

### Backend/DB

- ciclo editorial e transições; rejeição de publicação sem aprovação;
- versão imutável e concorrência otimista;
- autoridades admin 401/403; isolamento e erros;
- público lê só PUBLISHED e não expõe IDs/autores/fontes não verificadas;
- conteúdos maliciosos são rejeitados ou retornam apenas como texto inerte;
- SQL direto prova FKs, versionamento e impossibilidade de adulterar histórico;
- V1–V12+ em Testcontainers vazio e Flyway validate no volume existente;
- nenhuma tabela de produto, cotação, apólice ou integração.

### Frontend

- `/demonstracao/icatu` funciona sem registro admin publicado e sem BFF;
- aviso “não oficial” permanece visível em todos os estados;
- CTA é navegação local apenas;
- fluxo mostra fronteiras operante/planejado/mock futuro com semântica correta;
- publicado/ausente/503/rede do conteúdo editorial;
- texto administrado hostil permanece inerte;
- admin permite revisão/governança com fixture de teste, mas runtime sem IdP continua 401;
- nenhuma chamada a Spider/Icatu/mock, coleta, armazenamento ou analytics;
- não quebra `/c/{token}`, catálogo ou oportunidades.

### Visual real

Browser em 1440×900, 768×1024, 390×844 e 320×568; screenshots **sem** token/credencial; foco, teclado, zoom 200%, contraste, sem scroll horizontal. Verificar página base e conteúdo publicado por fixture isolada. Executar também a auditoria visual herdada da jornada `/c/{token}`; se impossível por ferramenta, declarar explicitamente o que ficou não verificado.

## 9. Documentação

Crie:

- `SEGSENSE_SRC_001.md` — fontes públicas Icatu, escopo de acesso e limitações;
- `SEGSENSE_UX_004.md` — âncora visual, narrativa, wireframe e estados;
- `SEGSENSE_DOM_003.md` — domínio editorial da demonstração;
- `SEGSENSE_DAT_006.md` — V12+ e invariantes;
- `SEGSENSE_API_007.md` — APIs editoriais **do SegSense**, não Satellite Contract;
- `SEGSENSE_SEC_004.md` — ameaça de alegação comercial indevida, conteúdo hostil e acesso;
- `SEGSENSE_REV_011.md` — revisão com evidências, ressalva visual e SAT;
- `SEGSENSE_PRM_011.md` — cópia integral deste prompt.

Atualize índice, PLN_001 e READMEs. Registre formalmente que o PRM_011 originalmente planejado para integração Spider foi **reprogramado** por dependência externa, sem marcar essa integração como realizada. Preserve `SEGSENSE_ADR_003` e `SEGSENSE_REQ_002`. Registre que PRM_012/013 tratarão da pesquisa verificável do portal e do provider mock independente, mas só após aprovação desta etapa.

## 10. Validação e ambiente

- Frontend: `npm ci`, lint, testes, build e audit; reportar resultados reais.
- Backend: `mvnw.cmd verify` completo; nenhuma exclusão de teste.
- Compose/PostgreSQL `:5437`, backend `:8088` profile `local`, frontend `:5178`; não apagar volume.
- HTTP real: nova rota pública, endpoints editoriais 401, respostas de conteúdo ausente/publicado em fixture, headers/CORS.
- Inspecionar logs, source, bundle e network para endpoints/segredos/PII.
- Hash do logo oficial antes/depois.
- Inspeção Git: alterações desta etapa apenas em `segsense/`; preservar trabalho sujo de outros produtos.
- Não fazer commit, push ou deploy.

## 11. Critérios de aceite

1. Página pública visualmente forte e imediatamente acessível, ainda que nenhum cenário admin esteja publicado.
2. Icatu identificada como **cenário demonstrativo não oficial**, sem falsa parceria ou marca gráfica.
3. Nenhuma promessa de produto, preço, cobertura, elegibilidade, contratação ou API não documentada.
4. Capacidades locais, dependência Spider e mock futuro visualmente e semanticamente separados.
5. Backoffice governa snapshots, fontes e publicação apenas editorial, com integridade também no PostgreSQL.
6. Conteúdo administrado não consegue remover disclaimers nem ativar chamada externa.
7. Browser/teclado/320 px comprovados ou lacuna visual explicitamente mantida.
8. PRM_009 não sofre regressão; SAT-03 continua não implementado.
9. Testes, builds, Flyway, HTTP, audit e segurança validados.
10. Nenhuma alteração fora de `segsense/`, nenhum commit/push/deploy.

## 12. Devolutiva obrigatória

Apresente em ordem:

1. fontes Icatu efetivamente acessíveis, URLs/datas e limites;
2. correção herdada visual da jornada `/c/{token}` ou lacuna;
3. arquivos criados/alterados;
4. decisão de UX da âncora e screenshots por viewport;
5. exatidão dos avisos de não oficialidade e fronteiras;
6. backoffice, estados, versionamento, aprovação e publicação;
7. V12+, constraints e testes SQL negativos;
8. APIs, 401/403 e público;
9. testes frontend/backend, audit, builds, Flyway e HTTP;
10. ambiente, hash do logo e Git;
11. SAT-01 a SAT-10;
12. ausências confirmadas: Spider, Icatu real, mock, produto, cotação, contratação, PII, login fictício, commit, push e deploy;
13. riscos jurídicos/comerciais e pontos ainda dependentes de autorização Icatu.

Não marque a etapa aprovada por conta própria.
