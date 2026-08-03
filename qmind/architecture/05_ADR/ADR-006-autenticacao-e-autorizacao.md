# ADR-006 — Autenticação e autorização

- Status: Aceito
- Aceito em: 2026-08-03
- Base de aceite: `../04_Docs/005_Monorepo_Confrontation.md`
- Data: 2026-08-03
- Responsáveis: equipe QMind

## Contexto

O QMind armazenará informações confidenciais de múltiplas organizações. Usuários poderão participar de uma ou mais organizações e possuir responsabilidades diferentes em cada uma. Autenticar uma identidade não é suficiente: cada ação precisa ser autorizada no tenant, recurso e estado corretos.

## Decisão proposta

Separar claramente **autenticação**, delegada preferencialmente a um provedor compatível com padrões abertos, de **autorização de negócio**, mantida pelo QMind.

A integração de identidade deverá usar OpenID Connect/OAuth 2.0 ou padrão equivalente adequado ao tipo de cliente. O produto não implementará armazenamento próprio de senhas se um provedor apropriado estiver disponível no ecossistema.

## Modelo de autorização

Adotar combinação de:

- papéis para capacidades gerais;
- atributos para organização, unidade, participação e estado do recurso;
- relacionamentos para autoria, designação e responsabilidade.

Papéis iniciais a validar:

- administrador da plataforma;
- administrador da organização;
- consultor ou auditor;
- gestor da qualidade;
- responsável por processo;
- responsável por ação;
- leitor ou observador.

Papéis não serão permissões universais: toda decisão considerará organização, ação e recurso.

## Princípios obrigatórios

- Negar por padrão.
- Aplicar menor privilégio.
- Verificar autorização em toda requisição e tarefa assíncrona.
- Não confiar em papéis, organização ou permissões enviados pela interface.
- Impedir enumeração e acesso por identificadores adivinhados.
- Registrar concessões, revogações e acessos administrativos relevantes.
- Testar explicitamente acessos negados e cruzados entre organizações.

## Sessões e autenticação forte

- Sessões terão expiração, revogação e proteção adequadas ao cliente.
- MFA será exigida para administradores e operações de risco; sua expansão aos demais perfis será definida por avaliação de risco.
- Opções resistentes a phishing deverão ser preferidas quando suportadas pelo provedor.
- Recuperação de conta será tratada como fluxo de segurança, com auditoria e proteção contra tomada de conta.
- Contas de serviço terão identidade própria, escopo mínimo e credenciais rotacionáveis.

## Administração e suporte

- Acesso de suporte não será implícito nem permanente.
- Impersonação, caso futuramente necessária, exigirá justificativa, consentimento ou política definida, duração limitada e auditoria visível.
- Usuário removido de uma organização perderá imediatamente os acessos correspondentes, preservando autoria histórica.
- O último administrador de uma organização não poderá ser removido sem transferência controlada.

## Alternativas consideradas

### Apenas RBAC

Não adotado isoladamente porque papel geral não captura organização, propriedade, designação e estado do recurso.

### Autorização somente na interface

Rejeitada. A interface não é uma fronteira de segurança.

### Sistema próprio de senhas

Não recomendado quando houver provedor adequado, devido ao custo e risco de autenticação, recuperação, MFA e resposta a incidentes.

## Consequências

### Positivas

- Autenticação especializada e autorização alinhada ao domínio.
- Política adequada a usuários vinculados a múltiplas organizações.
- Menor privilégio e testes mais claros.

### Negativas e riscos

- Regras baseadas em atributos e relações exigem política central e boa observabilidade.
- Integração com provedor cria dependência operacional.
- Revogação e sincronização de associações precisam de tratamento cuidadoso.

## Critérios para escolher o provedor

- compatibilidade com o monorepo e padrões abertos;
- MFA e opções resistentes a phishing;
- organizações, federação empresarial e ciclo de vida de usuários;
- revogação, auditoria, disponibilidade e exportação;
- privacidade, residência de dados, custo e suporte;
- prevenção de dependência proprietária excessiva.

## Confronto com o monorepo (aceite)

Decisões fechadas após inventário:

- O monorepo **não** oferece IdP OIDC pronto. Hub armazena senhas; inove usa código por e-mail + sessão.
- **Alvo do QMind:** autenticação via **OIDC (AWS Cognito)** na região operacional `us-east-2`, com MFA para administradores.
- **Proibido** reutilizar o armazenamento de senhas do Hub.
- **Transição de desenvolvimento:** código por e-mail (padrão inove/SES) é aceitável apenas em ambiente de desenvolvimento/piloto interno, sem senhas próprias e sem dados reais de clientes, até Cognito estar operacional.
- Autorização de negócio permanece no QMind (papéis + atributos + relações). Matriz papel×ação×recurso será elaborada com o modelo de domínio.

## Referências

- NIST SP 800-63B, Authentication and Authenticator Management: https://pages.nist.gov/800-63-4/sp800-63b.html
- OWASP Authorization Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- `ADR-002-isolamento-multiempresa.md`

