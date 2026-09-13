# SEGSENSE_PRM_009_COR_001 — Correção única da instância contextual

## Controle

- Projeto: SegSense
- Identificador: SEGSENSE_PRM_009_COR_001
- Versão: 1.1
- Data: 12/09/2026
- Vínculo: corretivo único do `SEGSENSE_PRM_009`
- Situação da etapa: **não aprovada** até a devolutiva deste corretivo

## Prompt para o Cursor

Execute **somente** esta correção em `C:\Projetos\segsense`. Leia integralmente o PRM_009, sua devolutiva, `SEGSENSE_REV_009`, `SEGSENSE_DAT_005`, `SEGSENSE_API_006`, `SEGSENSE_SEC_003`, V9 e os componentes/casos de uso envolvidos. Preserve V1–V9, dados e volume existentes. Não altere Spider, Panne, `.cursor/` nem outro produto. Não faça commit, push ou deploy.

Esta é a **única oportunidade de correção** do PRM_009. Não acrescente escopo de PRM_010, Spider, Icatu ou mock. Corrija os desvios abaixo e prove cada um por testes negativos e evidência real.

## 1. Credencial bruta retida no servidor — bloqueador de segurança

`ManageContextInstanceUseCase` guarda `rawCredential` em um `ConcurrentHashMap<String, IssuedCredential>` sem TTL, limite, limpeza ou persistência coordenada. Isso contradiz a promessa de valor bruto apenas na criação e torna o segredo recuperável em memória global, inclusive após retirada/expiração. Elimine totalmente esse cache de credenciais brutas.

Defina idempotência segura:

- `Idempotency-Key` **obrigatória**, com formato/entropia e tamanho validados, e digest persistido;
- mesma chave + mesmo contexto após a primeira criação não gera nova instância;
- nunca devolver a credencial novamente depois da resposta inicial;
- replay sem a credencial não pode ser interpretado como sessão utilizável pelo frontend: responda com conflito/estado explícito e orientação humana para iniciar uma nova tentativa **com nova chave**; não revele ID interno, digest nem estado sensível;
- corrida concorrente pela mesma chave deve resolver pela unique constraint sem criar duplicata nem vazar segredo;
- o cliente deve manter a mesma chave durante retry incerto, mas entender o caso em que a resposta inicial se perdeu; não tentar prosseguir com `instanceCredential=null`;
- não adicionar cache substituto com segredo em claro, inclusive em Redis ou JVM.

Teste criação, replay, resposta inicial perdida, concorrência, expiração e retirada. Inspecione heap-facing source e prove que nenhum singleton armazena credencial bruta.

## 2. Integridade relacional de valores e notice — bloqueador de dados

A V9 dá a `context_instance_value` uma FK independente para `instance_id` e outra para `snapshot_id`. SQL direto pode, portanto, ligar uma instância A a campo de um snapshot B. `consent_notice_field` também usa FKs independentes para snapshot e definição, permitindo definição de outra revisão. Crie **V10 incremental** com pré-validação fail-fast e constraints compostas que amarrem:

1. campo do notice ao snapshot da **mesma** `opportunity_revision_id`;
2. valor à instância e ao **mesmo** `notice_snapshot_id`/revisão;
3. field key, type, source e classification à definição imutável correta;
4. se aplicável, decisão ao notice/version/hash da mesma instância.

Teste INSERT/UPDATE SQL direto com snapshot cruzado, revisão cruzada, campo PUBLISHER, classificação indevida, tipo divergente e instância de outro escopo. Todos devem falhar no banco. Preserve FKs anteriores e não use cascade destrutivo. Não reescreva V9.

## 3. Aprovação de aviso sem justificativa — bloqueador de governança

`ConsentNoticeRequest` possui `justification`, mas o controller/use case/domain de `/approve` o ignoram. Exija justificativa administrativa não vazia, validada no domínio, registrada em trilha imutável com ator, versão, hash e timestamp UTC. A aprovação sem justificativa deve falhar. A retirada já exige justificativa: assegure que ela também fique persistida como evidência, não apenas validada e descartada. Não exponha autoria técnica na página pública.

Revise também a imutabilidade SQL dos snapshots e campos aprovados: uma atualização direta não pode alterar o texto/hash/definições que uma decisão posterior afirma ter apresentado. Implemente proteção no banco sem bloquear a criação legítima de novas versões DRAFT. Testes SQL de UPDATE/DELETE em snapshot aprovado e seus campos devem falhar.

## 4. Sessão pública e formulário — bloqueador funcional/UX

O frontend hoje mantém a credencial em variável de módulo (`instanceCredential.ts`), partilhada por qualquer montagem da aplicação; não a limpa ao trocar token/rota ou desmontar. Coloque-a no escopo da jornada ativa (state/ref não renderizado) e limpe-a ao desmontar, retirar autorização e iniciar nova jornada. Nunca persistir em storage/cookie nem mostrar em DOM/log. Alterar `/c/token-A` para `/c/token-B` não pode enviar o segredo de A para B.

`PublicProgressiveJourney` renderiza BOOLEAN como input de texto e converte qualquer coisa diferente de `"true"` em `false`. Substitua por controle explícito acessível de Sim/Não ou equivalente; vazio deve permanecer ausente, não virar falso. DATE, NUMBER e ENUM devem validar sem coerção silenciosa, com erro por campo associado ao input, resumo de erros e foco no primeiro inválido. Faça progressão em blocos curtos quando houver muitos campos, com ação **Voltar** até a revisão. A revisão deve permitir corrigir valores antes da autorização. Nunca autorize por Enter acidental numa etapa anterior.

O texto público não deve afirmar que a sessão foi encerrada se a credencial ainda estiver retida em memória. Diga precisamente que **recarregar ou fechar** a página impede retomada nesta etapa; mudança de rota deve efetivamente limpar o segredo.

## 5. Retirada e expiração

A retirada deve funcionar enquanto a sessão for válida. Verifique que estado `AUTHORIZED` não pode ser reutilizado para mutações após link/notice não efetivos, e que a interface descreve honestamente quando a retirada não é mais possível. Não alegue exclusão definitiva de valores. Mantenha decisão append-only e idempotência sem resposta contraditória.

## 6. Testes e evidências obrigatórias

- Backend `mvnw.cmd verify` completo, incluindo Testcontainers V1–V10 em banco vazio e Flyway validate no volume existente sem `down -v`.
- Testes de domínio, HTTP/security e SQL direto para todos os bloqueadores acima.
- Frontend `npm ci`, lint, testes e build; testes de BOOLEAN (ausente/false/true), DATE/NUMBER/ENUM inválidos, voltar/revisar, erro associado/foco, troca de rota, replay idempotente sem credencial e retirada.
- Browser real em 1440×900, 768×1024, 390×844 e 320×568, zoom 200% e teclado. Para fluxo de sucesso inacessível sem IdP, use fixture isolada de teste/evidência, nunca mock embutido em runtime de produção. Se browser não estiver disponível, declare explicitamente a lacuna; não a substitua por alegação visual.
- HTTP real para rotas públicas/admin, 401/403, CORS/origin e cabeçalhos de não armazenamento.
- Inspeção de logs/source/bundle por credencial, token, valores, storage, cookie, analytics, `dangerouslySetInnerHTML` e chamadas externas.
- Git: zero alterações novas fora de `segsense/`; logo original com SHA-256 preservado.

## 7. Documentação

Crie cópia integral deste prompt em `documents/SEGSENSE_PRM_009_COR_001.md`. Atualize `SEGSENSE_REV_009` para v1.1, `SEGSENSE_DAT_005`, `SEGSENSE_API_006`, `SEGSENSE_SEC_003`, `SEGSENSE_FUN_002`, `SEGSENSE_UI_001`, PLN, índice e README onde afetados. Registre precisamente limites residuais, inclusive ausência de IdP e de retomada após reload. Não declare conformidade jurídica concluída.

## 8. Devolutiva

Apresente uma matriz de cada item 1–5 com: causa, arquivos alterados, proteção implementada, teste negativo, resultado. Inclua V10 e provas SQL, política de idempotência, ciclo de vida da credencial, evidência da justificativa, UX por tipo de campo, testes/builds, browser/limitações, ambiente final, hash do logo, SAT-01 a SAT-10 e Git. Se algo permanecer falho, declare-o; não marque a etapa aprovada por conta própria.

Não faça commit, push ou deploy.
