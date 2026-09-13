# SEGSENSE_PRM_002

Cópia integral do prompt de execução da etapa `SEGSENSE_PRM_002`.

---

Implemente o `SEGSENSE_PRM_002` no produto `C:\Projetos\segsense`, dentro do monorepo Git existente `leaction-ecosystem`.

Antes de alterar arquivos, leia integralmente:

- `documents/SEGSENSE_ARQ_001.md`;
- `documents/SEGSENSE_PLN_001.md`;
- `documents/SEGSENSE_REV_001.md`;
- `documents/references/SPIDER-ARCH-017.md`;
- `README.md`;
- `backend/pom.xml`;
- todo o código atual do backend e do frontend.

Procure e cumpra `AGENTS.md` ou instruções equivalentes. Preserve alterações preexistentes. Não execute `git init`, não altere remotes, não modifique outros produtos e não faça commit, push ou deploy.

## 1. Objetivo

Formalizar e aplicar a arquitetura interna do SegSense como **Insurance Reference Satellite**, consolidando:

- backend Java como Satellite BFF;
- separação entre domínio, aplicação, entrada HTTP e infraestrutura;
- identidade local única do satélite;
- manifesto preliminar explicitamente não certificado;
- convenções de API, erros, identificadores, tempo e correlação;
- fronteira entre estado local e projeções operacionais da Spider;
- testes arquiteturais automatizados;
- documentação das decisões.

Não implementar integração, client ou mock da Spider/Icatu, submissão de objetivo, Intent Contract, execução assíncrona, jornada de seguros, autenticação de usuários ou regras funcionais de seguros.

## 2. Correções herdadas da etapa anterior

Execute antes do novo escopo:

1. Em `documents/README.md`, corrigir a versão de `SEGSENSE_ARQ_001` de 0.1 para 0.2.
2. Em `documents/SEGSENSE_REV_001.md`, corrigir dependências e referências que identifiquem o ARQ vigente como v0.1; o correto é v0.2.
3. Corrigir a conclusão de `SEGSENSE_REV_001`: ARQ §12 e SPIDER-ARCH-017 não constituem mais conflito normativo aberto, porque o adendo ARQ §26 declara expressamente a precedência do SPIDER-ARCH-017. Registrar que a questão está resolvida arquiteturalmente: a Icatu será executor potencial resolvido pela Spider, não integração operacional direta do SegSense.
4. Preservar o histórico da revisão: elevar `SEGSENSE_REV_001` para v1.2 e descrever as correções.
5. Validar que o índice documental continua apontando para arquivos existentes.

Não prossiga ao novo escopo enquanto essas verificações não estiverem concluídas.

## 3. Identidade do satélite

Adote `SEGSENSE` como `applicationId` único.

Centralize-o em configuração externa tipada; não o espalhe como literal pelo código.

Acrescente `applicationId` à resposta de:

`GET /api/v1/system/info`

Mantenha os campos atuais e atualize os tipos, a interface e os testes do frontend.

Essa identidade é local. Não declare autenticação ou registro aceito pela Spider.

## 4. Satellite BFF

Documente e imponha que:

- Browser/React chama somente o BFF SegSense;
- o BFF será a única fronteira futura com o Satellite Contract;
- credenciais técnicas nunca chegam ao frontend;
- o BFF não interpreta intent nem escolhe plano, capability, route, adapter ou executor;
- operações exclusivamente locais não precisam passar pela Spider.

## 5. Manifesto preliminar

Crie:

`backend/src/main/resources/satellite-manifest.yaml`

O manifesto deverá ser explicitamente classificado como `DRAFT / NOT_CERTIFIED` e conter apenas:

- `schemaVersion` local claramente marcado como preliminar;
- `applicationId: SEGSENSE`;
- domínio `INSURANCE`;
- classes pretendidas `READ`, `SIMULATE`, `REQUEST`;
- `mutationPolicy: CONFIRMATION_REQUIRED`;
- status `DRAFT`;
- indicação de que não é contrato executável nem aceito pela Spider.

Não inclua routes, adapters, URLs, credenciais, produto Icatu, capabilities inventadas ou permissões tratadas como concedidas.

Carregue e valide o arquivo na inicialização do backend apenas como configuração local. A aplicação deverá falhar claramente se o `applicationId` do manifesto divergir da configuração.

Não envie o manifesto a nenhum sistema.

## 6. Correlação HTTP local

Implemente correlação para requisições `/api/**`:

- header `X-Correlation-ID`;
- aceitar o valor recebido somente quando for UUID válido;
- gerar UUID quando ausente ou inválido;
- devolver no response o identificador efetivamente utilizado;
- disponibilizá-lo durante a requisição;
- incluí-lo no MDC dos logs;
- removê-lo do MDC ao final;
- incluir `correlationId` no corpo padronizado de erros;
- não confundi-lo com `requestId`, `decisionId`, `planId`, `executionId` ou `interactionId` da Spider;
- documentar que o mapeamento futuro dependerá do Satellite Contract executável.

Atualize CORS para permitir `X-Correlation-ID`, mantendo origem explícita e sem curinga.

No frontend, envie um UUID por chamada técnica e valide nos testes que a requisição contém o header. Não armazene o identificador indefinidamente nem o use para rastreamento de usuário.

## 7. Convenções técnicas

Adote e documente:

- JSON em UTF-8;
- datas e instantes em ISO-8601 UTC;
- UUID para identificadores distribuídos;
- URLs versionadas em `/api/v1`;
- nomes de código em inglês;
- mensagens destinadas ao usuário em português;
- códigos de erro estáveis em inglês e `UPPER_SNAKE_CASE`;
- ausência de stack trace, classe, SQL ou segredo nas respostas;
- uma convenção justificada para paginação futura, sem criar endpoint fictício;
- idempotência futura para mutações, sem inventar header incompatível com a Spider;
- propagação futura dos IDs canônicos da Spider sem colapsá-los em um único campo.

## 8. Arquitetura interna

Organize o backend conforme:

```text
domain <- application <- inbound/infrastructure
```

Regras:

- `domain` não depende de Spring, JPA, servlet, HTTP ou infraestrutura;
- `application` contém casos de uso e portas, sem depender de controllers ou implementações externas;
- `inbound/http` adapta HTTP para casos de uso;
- `infrastructure` contém configuração e adapters técnicos;
- nenhuma camada cria Intent Router, Context Guard, Execution Plan ou Capability Resolver;
- componentes locais de health não devem ser apresentados como domínio de seguros;
- não criar pacotes vazios apenas para satisfazer o desenho.

Refatore somente o necessário. Preserve os endpoints e comportamentos já validados.

Adicione ArchUnit e crie regras automatizadas que comprovem:

1. domínio independente de Spring, JPA e HTTP;
2. aplicação independente de `inbound`;
3. ausência de dependências para routes ou adapters internos da Spider;
4. controllers restritos à camada inbound HTTP.

Não use testes frágeis de nome quando uma dependência puder ser verificada diretamente.

## 9. Documentação obrigatória

Crie `documents/SEGSENSE_ARQ_002.md` contendo:

- contexto e objetivo;
- diagrama Browser → React → Satellite BFF → Satellite Contract futuro → Spider;
- componentes e responsabilidades;
- dependências permitidas e proibidas;
- estado local versus projeção Spider;
- identidade `SEGSENSE`;
- manifesto preliminar;
- correlação local e IDs Spider futuros;
- segurança da fronteira;
- tratamento de indisponibilidade;
- consequências e limitações;
- mapa SAT-01 a SAT-10 após esta etapa.

Crie `documents/SEGSENSE_ADR_001.md`, com o título:

> Icatu como executor resolvido pela Spider

Registre contexto, decisão, alternativas rejeitadas e consequências. Declare proibida a integração operacional direta SegSense–Icatu para operações pertencentes ao plano Spider.

Crie `documents/SEGSENSE_API_001.md` documentando:

- convenções HTTP;
- versionamento;
- correlação;
- erros;
- datas;
- identificadores;
- CORS;
- compatibilidade;
- somente exemplos de endpoints realmente existentes.

Crie `documents/SEGSENSE_REV_002.md` registrando evidências, aderência, riscos, débitos e avaliação honesta de SAT-01 a SAT-10.

Registre uma cópia integral deste prompt em:

`documents/SEGSENSE_PRM_002.md`

Atualize `documents/README.md` com todos os documentos e versões corretas.

## 10. Testes obrigatórios

Backend:

- carregamento válido do manifesto;
- falha de validação quando o `applicationId` divergir;
- system info contendo `applicationId`;
- correlação preservada para UUID válido;
- UUID gerado quando header estiver ausente;
- UUID novo quando header for inválido;
- `correlationId` no erro padronizado;
- remoção do MDC após requisição;
- regras ArchUnit;
- regressão de health, readiness, Flyway e Testcontainers.

Frontend:

- leitura do novo `applicationId`;
- envio de `X-Correlation-ID` válido;
- renderização do estado disponível;
- estado indisponível real;
- rejeição segura de payload inválido;
- lint e build.

Não reduza cobertura nem remova testes anteriores.

## 11. Validações finais

Execute:

1. `backend\mvnw.cmd verify`;
2. `npm ci` no frontend;
3. lint, testes e build do frontend;
4. validação do Compose sem recriar o volume;
5. inicialização ou reinicialização controlada do backend, se necessária;
6. chamadas reais a system info, health e readiness;
7. chamada real com `X-Correlation-ID` válido, confirmando o response header;
8. chamada real com header inválido, confirmando substituição por UUID;
9. verificação de CORS para a origem autorizada e o novo header;
10. inspeção por segredos e artefatos indevidos;
11. estado Git restrito a `segsense/`.

Não apague volumes ou dados. Se houver bloqueio ambiental, relate-o sem simular sucesso.

## 12. Critérios de aceite

- Correções herdadas concluídas e documentadas.
- Backend formalizado como Satellite BFF sem client Spider.
- `applicationId=SEGSENSE` centralizado, validado e exposto.
- Manifesto DRAFT validado localmente e não tratado como certificado.
- Correlação HTTP funcionando e testada.
- Erros incluem correlação sem expor detalhes internos.
- Arquitetura de camadas protegida por testes.
- Frontend continua refletindo o estado real.
- ARQ_002, ADR_001, API_001, REV_002, PRM_002 e índice existem.
- Icatu permanece executor potencial resolvido pela Spider.
- Nenhuma integração, intent, plano, capability ou jornada foi inventada.
- Testes e builds passam.
- Nenhum outro produto foi alterado.

## 13. Devolutiva obrigatória

Apresente:

1. correções herdadas;
2. arquivos criados e alterados;
3. decisões arquiteturais;
4. árvore relevante;
5. comportamento do manifesto e da correlação;
6. comandos e resultados;
7. evidências HTTP reais;
8. resultado dos testes ArchUnit;
9. avaliação SAT-01 a SAT-10;
10. estado Git limitado a `segsense/`;
11. riscos, ressalvas e itens não implementados;
12. confirmação de ausência de integração fictícia e de alterações em outros produtos.

Não faça commit, push ou deploy.
