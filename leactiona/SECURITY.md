# Diretrizes de Segurança — LEACTIONA.COM.BR

Fonte: fase Phanton `security_guidelines` · pipeline `leactiona-lms-migration`.

Referências citadas: OWASP ASVS 5.0 (Level 3 onde aplicável), FAPI 2.0, OWASP API Security Top 10, LGPD.

---

## Diretrizes gerais

1. Implementar transporte seguro utilizando TLS 1.3 (ou TLS 1.2 com cipher suites fortes) em todas as comunicações, conforme exigido pelo FAPI 2.0 e ASVS 5.0.
2. Configurar cabeçalhos de segurança HTTP rígidos (HSTS, Content Security Policy - CSP, X-Content-Type-Options, Referrer-Policy) para mitigar ataques no Next.js SPA.
3. Implementar rate limiting e proteção contra abuso de recursos em nível de API Gateway/CloudFront para mitigar ataques de negação de serviço (OWASP API Security Top 10 - API4: Unrestricted Resource Consumption).
4. Garantir que nenhum dado pessoal identificável (PII) ou credencial seja registrado em logs de depuração da aplicação, em conformidade com o princípio de segurança e limitação de finalidade da LGPD.
5. Adotar criptografia em trânsito e em repouso para todos os fluxos de dados da aplicação (ASVS 5.0).

---

## Por módulo

### auth-rbac

- Implementar autenticação baseada em tokens JWT assinados com algoritmos assimétricos (RS256 ou ES256) e tempo de expiração curto (máximo 15 minutos), utilizando refresh tokens seguros (ASVS 5.0).
- Adotar os requisitos de segurança do perfil FAPI 2.0, utilizando PKCE (Proof Key for Code Exchange) e tokens restritos ao remetente (DPoP - Demonstrating Proof-of-Possession) para mitigar roubo de sessão.
- Enforçar controle de acesso baseado em papéis (RBAC) estrito no backend para os papéis ADMIN, TEACHER e STUDENT, validando a autorização em cada requisição para evitar Broken Function Level Authorization (OWASP API Security Top 10 - API5).
- Implementar política de senhas forte (mínimo de 12 caracteres, verificação contra dicionários de senhas expostas) e armazenamento de senhas utilizando hash robusto como Argon2id ou bcrypt (ASVS 5.0 Level 3).

### lms-engine

- Enforçar validação de autorização em nível de objeto (BOLA) em todas as rotas de lições e cursos, garantindo que o aluno logado possua uma matrícula ativa (`Enrollment.is_paid_access` ou `Course.is_free`) antes de expor o conteúdo (OWASP API Security Top 10 - API1).
- Gerar URLs assinadas e temporárias (AWS CloudFront Signed URLs) com tempo de expiração curto para o consumo de mídias (vídeos, PDFs, áudios) armazenadas no S3, impedindo o acesso direto e não autorizado aos arquivos (ASVS 5.0).
- Implementar logs de auditoria imutáveis para ações administrativas críticas, como alteração manual de status de matrícula (`is_paid_access`) e exclusão de dados de usuários (ASVS 5.0).

### player-xapi

- Garantir que a comunicação entre o frontend/backend e o LRS externo (Learning Locker) utilize autenticação forte baseada em credenciais seguras (mTLS ou chaves de API transmitidas de forma segura via HTTPS) conforme FAPI 2.0.
- Sanitizar e validar rigorosamente a estrutura de todos os statements xAPI recebidos e enviados para evitar injeções de scripts (XSS) e garantir a integridade dos dados de progresso (OWASP API Security Top 10 - API8).
- Implementar verificação de assinatura digital (HMAC-SHA256) em webhooks recebidos do LRS para garantir a autenticidade e integridade dos dados de progresso sincronizados de forma assíncrona.

### database-core

- Implementar criptografia em repouso (Encryption at Rest) para o banco de dados PostgreSQL utilizando chaves gerenciadas via AWS KMS (ASVS 5.0).
- Utilizar exclusivamente consultas parametrizadas através do Prisma ORM para neutralizar riscos de SQL Injection (OWASP API Security Top 10 - API8 / ASVS 5.0).
- Aplicar criptografia em nível de aplicação (AES-256-GCM) para dados pessoais sensíveis dos alunos (como CPF, e-mail e nome completo) antes da persistência no banco de dados, garantindo conformidade com o Artigo 46 da LGPD.

### gamification-badges

- Processar e calcular todas as regras de pontuação, conquistas e ranking estritamente no lado do servidor (server-side), baseando-se em dados de progresso validados e nunca confiando em inputs diretos do cliente (ASVS 5.0).
- Implementar controle de concorrência e idempotência no processamento de eventos de gamificação para evitar condições de corrida (Race Conditions) que permitam a duplicação ilícita de pontos ou badges.

### certificate-generator

- Gerar os arquivos PDF de certificados em tempo de execução utilizando a biblioteca `pdfkit` no backend, aplicando sanitização estrita de inputs para evitar ataques de injeção de conteúdo no PDF (ASVS 5.0).
- Validar rigorosamente no backend, imediatamente antes da geração do PDF, se o aluno cumpre todos os requisitos acadêmicos (100% de progresso e nota mínima), impedindo a geração fraudulenta de certificados por manipulação de requisições (OWASP API Security Top 10 - API1 / API5).
- Garantir que os certificados gerados sejam transmitidos diretamente como stream para o usuário autenticado ou armazenados em bucket privado do S3 com acesso restrito, impedindo a exposição pública de dados pessoais de terceiros (LGPD).

---

## Mapa módulo → artefato esperado

| Módulo Phanton | Escopo |
|----------------|--------|
| `auth-rbac` | JWT RS256/ES256, refresh, PKCE/DPoP, RBAC, senhas |
| `lms-engine` | BOLA matrícula, signed URLs, audit log admin |
| `player-xapi` | LRS auth, sanitize xAPI, webhook HMAC |
| `database-core` | KMS at-rest, Prisma, AES-GCM app-level PII |
| `gamification-badges` | server-side scores, idempotência |
| `certificate-generator` | pdfkit + 100%/nota≥70 + stream autenticado (sem QR) |
