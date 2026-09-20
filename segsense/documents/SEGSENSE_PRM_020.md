# SEGSENSE_PRM_020 — Ingestão real e segura de URL, revisão do contexto e possibilidades compatíveis

## Controle

- Projeto: SegSense. Versão 1.0. Data: 15/09/2026.
- `SEGSENSE_PRM_019_COR_001` encerrado **APROVADO COM RESSALVA BLOQUEANTE**: a jornada residencial e o prêmio simulado foram executados de ponta a ponta, mas uma URL pública real ainda podia ser aceita pela interface sem ser efetivamente processada.
- Este PRM transforma URL pública em fonte funcional de contexto. Não se admite fixture silenciosa, substituição por exemplo governado, sucesso vazio, inferência apresentada como fato ou resposta sem evidência de execução.
- Cursor executa no monorepo `leaction-ecosystem`, na branch vigente, preservando aplicações independentes: SegSense → Satellite Contract → Spider → Provider Contract → provider/mock. Alterações somente em `segsense/`, `spider/` e `segsense-provider-mock/` quando necessárias. Não tocar Experience Hub, Panne ou outros produtos.
- Não fazer commit, push ou deploy. Novos documentos originados daqui usam prefixo `SEGSENSE_`.

## Objetivo verificável

Ao informar uma URL pública real — inclusive um artigo sobre quebra de safra — e declarar uma intenção, a pessoa deve receber uma destas respostas verdadeiras:

1. o SegSense obteve o conteúdo, mostrou exatamente o contexto extraído para revisão, a pessoa o confirmou e a Spider processou contexto + intenção, retornando somente possibilidades realmente disponibilizadas por uma capability/provider registrado; ou
2. o SegSense não conseguiu obter ou compreender conteúdo suficiente e explicou o motivo, sem chamar a Spider ou o provider indevidamente e sem substituir a URL por conteúdo sintético.

O botão nunca pode parecer inerte. Toda tentativa termina em estado visível e correlacionado.

## Prompt para o Cursor

Leia integralmente `SEGSENSE_PRM_019`, `SEGSENSE_PRM_019_COR_001`, `SEGSENSE_FUN_004`, `SEGSENSE_ADR_007`, `SEGSENSE_JRN_EVID_001`, `SEGSENSE_OPS_001`, os contratos Satellite 1.0/1.1, Provider 1.0/1.1, registros de capabilities, migrations e implementação real das três aplicações. Antes de alterar código, documente a matriz:

`URL digitada → validação → resolução DNS → conexão/redirect → resposta HTTP → bytes recebidos → extração → snapshot → revisão humana → contexto confirmado → intenção → Spider → capability → provider → possibilidades exibidas`.

Cada seta deve indicar executor, evidência persistida, erro possível e dado que atravessa a fronteira.

## 1. Separar captura, confirmação e processamento

Reestruture a jornada pública em ações inequívocas:

1. **Obter conteúdo da URL**: inicia somente a captura server-side pelo SegSense.
2. **Revisar contexto extraído**: mostra título, domínio, URL final, data/hora da captura, trecho textual efetivamente extraído e elementos estruturados. Diferencie claramente texto da fonte, elementos extraídos automaticamente e complementos declarados pela pessoa.
3. **Confirmar este contexto**: a pessoa confirma ou corrige os elementos antes de qualquer envio à Spider. Correções tornam-se contribuição `USER_DECLARED`, sem apagar a contribuição `URL_EXTRACTED` original.
4. **Informar intenção**: campo livre e corrigível, independente do link.
5. **Ver possibilidades para este contexto**: envia ao BFF somente depois de contexto confirmado e intenção suficiente.

Não reutilize o mesmo botão para captura, confirmação e processamento. Preserve o que a pessoa já digitou quando uma etapa falhar. Qualquer clique deve produzir carregamento honesto e depois sucesso ou erro visível. Não use timer para simular progresso.

Os exemplos governados podem continuar como demonstrações nomeadas, mas devem ser visualmente separados da entrada “URL pública”. Selecionar exemplo governado não pode ocorrer automaticamente quando uma URL real falhar.

## 2. Captura real da URL no SegSense

Implemente um componente server-side próprio no boundary do SegSense para obter **uma única página indicada pela pessoa**. O navegador não faz fetch direto e CORS não serve como solução. Não execute JavaScript remoto, não use browser headless nesta etapa e não faça crawling.

Aceite apenas `http`/`https`, preferindo HTTPS. Rejeite userinfo, fragmento operacional, portas não permitidas, URL malformada e host sem resolução pública. Antes de cada conexão e de cada redirect, resolva e valide todos os endereços: bloquear loopback, link-local, redes privadas, multicast, unspecified, metadata/cloud endpoints, IPv4 embutido em IPv6 e mudanças de destino por DNS rebinding. Limite redirects e exija revalidação completa em cada salto. Não encaminhe cookies, credenciais, cabeçalhos internos, tokens, `Authorization`, referer sensível ou IP do visitante.

Defina limites explícitos e configuráveis: tempo de conexão/leitura, tamanho máximo da resposta, quantidade de redirects, tipos MIME aceitos e charset. Para o MVP, aceite HTML textual e, somente se implementado e testado de forma segura, texto puro; demais formatos retornam erro claro. Faça streaming com corte por limite, não carregue resposta ilimitada. TLS inválido não pode ser ignorado.

Registre apenas metadados seguros. Nunca grave ou devolva segredos encontrados na página. Sanitize logs contra quebra de linha e conteúdo hostil. Não renderize HTML remoto nem use `dangerouslySetInnerHTML`; converta para texto inerte.

## 3. Extração, snapshot e proveniência verificáveis

Da resposta efetivamente recebida, produza um snapshot imutável com, no mínimo:

- URL solicitada e URL final após redirects;
- domínio final;
- instante UTC da captura;
- status HTTP e tipo de conteúdo;
- título extraído, idioma quando detectável e texto principal normalizado;
- hash SHA-256 dos bytes recebidos e hash do texto normalizado;
- versão do extrator;
- resultado `FETCHED`, `UNSUPPORTED_CONTENT`, `TOO_LARGE`, `TIMEOUT`, `DNS_BLOCKED`, `REDIRECT_BLOCKED`, `HTTP_ERROR`, `NO_MEANINGFUL_TEXT` ou equivalente documentado.

Não alegue autoria, data de publicação ou tema se não estiverem presentes/detectáveis. Metadado de publicação extraído deve ficar distinto do horário de captura. Não copie imagens, scripts, formulários ou página integral para a UI. Mostre trecho suficiente para revisão e permita expandir texto extraído dentro de limites razoáveis.

A extração de elementos contextuais deve ser determinística e explicável nesta etapa. Não invente fatos ausentes. Cada elemento estruturado precisa carregar evidência apontando para trecho do snapshot ou ser marcado como declaração/correção do usuário. Elementos sem suporte não entram no contexto confirmado.

Persista captura, snapshot e confirmação de forma relacional e append-only quando aplicável, usando migration incremental. Não reescreva V1–V16. Defina retenção e minimização adequadas ao MVP; não trate a URL como inofensiva, pois ela pode conter identificadores.

## 4. Quebra de safra: contexto real sem produto inventado

Use no teste uma URL pública real e acessível sobre quebra de safra fornecida durante a execução ou configurada como fixture **HTTP controlada de integração** apenas para testes automatizados. A fixture de teste deve simular transporte HTTP; ela não pode ser mostrada como se fosse a URL real auditada.

Quando o conteúdo real falar de quebra de safra, a UI poderá mostrar elementos como tema, evento, cultura/região/período **somente se esses elementos estiverem no texto obtido**. A intenção deve continuar declarada livremente, por exemplo: “Quero entender opções de proteção para perda de produção”. Não deduza que a pessoa é produtora, proprietária, está naquela região ou sofreu perda.

A Spider deve receber contribuição com provenance `URL_EXTRACTED` (ou nome versionado equivalente), hashes/referência do snapshot e contribuição separada da intenção `USER_DECLARED`. Se o Satellite Contract 1.1 não comportar a provenance sem perda semântica, faça evolução versionada e compatível; nunca relabele o contexto como `SATELLITE_GOVERNED` ou esconda texto/hashes em `scenarioKey`.

Para produzir a âncora comercial “contexto → possibilidades”, registre no provider demonstrativo uma capability agrícola distinta, por exemplo `DISCOVER_SYNTHETIC_CROP_PROTECTION_PATHS`. O retorno deve ser efetivamente gerado pelo provider/mock nesta execução e conter possibilidades claramente marcadas como demonstrativas, com pertinência, dados ainda necessários e limites. O SegSense não hardcodeia cartões de seguro.

Não invente prêmio agrícola, cobertura, seguradora, elegibilidade ou produto comercial. Sem regra de rating autorizada, o provider deve retornar caminhos de conversa/serviço e perguntas necessárias, **sem R$**. A cotação residencial existente continua independente e só pode ser usada para contexto/intenção residencial compatível. Quebra de safra nunca pode cair no simulador residencial.

Se o provider não tiver capability compatível, a Spider deve responder honestamente `NO_COMPATIBLE_CAPABILITY` (ou status versionado equivalente), e a UI deve dizer que não há possibilidade disponível neste ambiente demonstrativo. Isso é resultado funcional, não erro silencioso.

## 5. Estados públicos obrigatórios

Projete linguagem humana para:

- URL pronta para captura;
- captura em andamento;
- conteúdo obtido e aguardando revisão;
- contexto corrigido/confirmado;
- URL inválida ou protocolo bloqueado;
- host privado/loopback/metadata bloqueado;
- timeout, redirect inseguro, HTTP 4xx/5xx, MIME não suportado, excesso de tamanho;
- página dependente de JavaScript ou sem texto significativo;
- intenção ausente/não compreendida;
- dados contextuais insuficientes, com perguntas específicas;
- nenhuma capability compatível;
- provider indisponível;
- possibilidades retornadas pelo provider;
- nova tentativa invalidando resultados anteriores.

Mensagens devem explicar o que ocorreu e o próximo passo. Não exponha enum, stack trace, endereço interno, segredo, regra de firewall ou detalhes de infraestrutura na superfície pública. IDs, hashes completos, versões e tempos técnicos ficam recolhidos em “Detalhes técnicos desta tentativa”.

## 6. Provas obrigatórias

Use uma stack isolada com ledger seguro, sem encerrar a stack antiga sem prova de propriedade. Prove por HTTP real e navegador:

1. URL pública real acessível → conteúdo realmente recebido, hash e snapshot persistidos;
2. trecho mostrado na UI existe no corpo obtido; nenhuma fixture governada o substitui;
3. revisão/correção cria contribuições distintas e preserva a fonte original;
4. intenção declarada é independente da URL;
5. quebra de safra + intenção compatível → Spider escolhe capability agrícola → mock é chamado → possibilidades exibidas são exatamente as retornadas;
6. quebra de safra não chama capability residencial e não mostra prêmio residencial;
7. ausência de capability → resultado honesto, sem cartões hardcoded;
8. URL inacessível/404/timeout/MIME excessivo → estado visível e Spider não chamada;
9. SSRF: localhost, IP privado, link-local/metadata, redirect para rede privada, IPv6 local e DNS rebinding simulado são bloqueados;
10. HTML hostil fica inerte; scripts não executam; conteúdo enorme é interrompido;
11. provider down não mostra possibilidade anterior;
12. replay idêntico e mudança material obedecem à idempotência;
13. fluxo residencial do PRM_019 continua retornando o prêmio correto pelo mock;
14. SegSense não chama diretamente nenhum provider.

Testes automatizados de captura devem usar servidor HTTP controlado localmente e injetar resolvedor/transport seguro para cobrir redirects, DNS e limites sem depender da internet. A prova da URL pública real é adicional e deve registrar data, URL e resultado, sem incorporar o conteúdo integral ao Git.

No navegador real, valide 1440×900, 768×1024, 390×844, 320×568, zoom 200%, teclado/foco e impressão. Não autorize microfone. Verifique que uma pessoa de seguros consegue distinguir: conteúdo capturado, interpretação, correção humana, intenção, decisão da Spider e possibilidade devolvida pelo provider.

Execute frontend completo (`npm ci`, lint, testes, build), `mvnw verify` completo do SegSense, suíte ampla pertinente da Spider, todos os testes do mock, validação Flyway em banco vazio e volume existente, preflight/ACL/segredos e inspeção de logs. Falhas de ambiente devem ser separadas de defeitos reais e reexecutadas de forma limpa.

## 7. Documentação

Crie e indexe:

- `SEGSENSE_PRM_020.md` — cópia integral deste prompt;
- `SEGSENSE_URL_001.md` — contrato funcional da captura, extração, revisão, erros e retenção;
- `SEGSENSE_SEC_004.md` — threat model da ingestão de URL e controles SSRF/conteúdo hostil;
- `SEGSENSE_FUN_005.md` — jornada contexto real + intenção + possibilidades;
- `SEGSENSE_DAT_006.md` — snapshots, hashes, contribuições e integridade relacional;
- `SEGSENSE_REV_020.md` — revisão e evidências.

Atualize `SEGSENSE_PLN_001`, `SEGSENSE_DEMO_RUN_001`, `SEGSENSE_JRN_EVID_001`, `SEGSENSE_OPS_001`, APIs/contratos afetados, READMEs e índice oficial. Toda decisão de versionamento deve ser explícita. Não apresente o mock como Icatu ou provider certificado.

## 8. Devolutiva

Comece mostrando, em linguagem de negócio, uma execução real:

`URL de quebra de safra → conteúdo capturado → elementos revisados → intenção declarada → decisão Spider → capability escolhida → possibilidades retornadas pelo provider`.

Depois informe:

- URL solicitada/final, horário, HTTP/MIME, hashes abreviados e versão do extrator;
- trecho/evidência que sustenta cada elemento;
- fronteiras e payloads sanitizados;
- provas de que não houve fixture substituta nem cartões hardcoded;
- matriz de falhas e SSRF;
- testes, migrations, stacks e Git;
- o que permanece demonstrativo e o que exigiria contrato real.

**Pare para auditoria. Não autoaprove e não inicie `SEGSENSE_PRM_021`.** Há no máximo um corretivo para este PRM original.
