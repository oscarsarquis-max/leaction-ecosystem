# ADR-009 — Hospedagem, observabilidade e continuidade

- Status: Aceito
- Aceito em: 2026-08-03
- Base de aceite: `../04_Docs/005_Monorepo_Confrontation.md`
- Data: 2026-08-03
- Responsáveis: equipe QMind

## Contexto

O QMind dependerá de API, aplicação web, banco, armazenamento, filas e fornecedores externos. A solução precisa operar com segurança, permitir diagnóstico de falhas e recuperar dados e serviços após incidentes. O provedor de nuvem e as ferramentas concretas ainda dependem do ecossistema existente e dos requisitos comerciais.

## Decisão proposta

Adotar **infraestrutura gerenciada e reproduzível**, preferencialmente no provedor já operado competentemente pelo ecossistema, desde que atenda isolamento, região, segurança, observabilidade, backup, custo e portabilidade do QMind.

O monólito modular poderá ser implantado como aplicação web e trabalhador assíncrono separados, usando o mesmo código-base e fronteiras de domínio. Banco, objetos, segredos e filas utilizarão serviços gerenciados quando isso reduzir risco operacional sem criar dependência desproporcional.

## Ambientes

- Desenvolvimento: dados sintéticos e recursos mínimos.
- Homologação: configuração semelhante à produção, sem dados reais por padrão.
- Produção: acesso restrito, mudanças auditáveis e recursos protegidos.

Contas, projetos ou assinaturas deverão separar produção de ambientes não produtivos. Credenciais e dados não serão compartilhados entre ambientes.

## Infraestrutura e implantação

- Infraestrutura será descrita de forma versionada e revisável.
- Artefatos serão imutáveis e promovidos entre ambientes.
- Mudanças de banco seguirão estratégia compatível com implantação gradual.
- Implantação terá verificação de saúde e mecanismo seguro de reversão ou correção.
- Segredos ficarão em serviço próprio, com rotação e acesso mínimo.
- Dependências externas terão timeouts, repetição limitada e circuitos de proteção quando aplicável.

## Observabilidade

### Logs

- Estruturados, com ambiente, serviço, correlação e organização pseudonimizada quando necessária.
- Sem senhas, tokens, evidências completas, prompts completos ou dados pessoais desnecessários.
- Acesso e retenção definidos por finalidade.

### Métricas

- disponibilidade, latência e erros por operação;
- filas, repetição e trabalhos falhos;
- conexões, consultas lentas e capacidade do banco;
- armazenamento, uploads e verificações;
- uso, custo, latência e falhas de IA;
- eventos de autorização negada e comportamento anômalo.

### Rastreamento e alertas

- Requisições e trabalhos assíncronos compartilharão correlação.
- Alertas serão acionáveis, com responsável e procedimento de resposta.
- Dados de observabilidade respeitarão isolamento e privacidade.

## Objetivos de serviço

Antes do piloto serão definidos indicadores e objetivos para:

- disponibilidade do fluxo principal;
- latência das operações interativas;
- sucesso de tarefas assíncronas;
- durabilidade de evidências;
- tempo de detecção e recuperação.

Os objetivos deverão refletir necessidade do negócio e orçamento, evitando compromissos não medidos.

## Backup e recuperação

- Banco terá backups automáticos, criptografados e política de retenção.
- Recuperação pontual será usada quando suportada e justificada.
- Objetos seguirão versionamento e proteção contra exclusão acidental conforme classificação.
- Configuração, infraestrutura e dependências necessárias à restauração serão versionadas.
- Backups serão isolados das credenciais operacionais sempre que possível.
- Restaurações serão testadas periodicamente; existência de backup sem teste não comprova recuperação.

RPO e RTO serão definidos por análise de impacto antes do uso de dados reais:

- RPO: perda máxima aceitável de dados medida em tempo.
- RTO: tempo máximo aceitável para restaurar o serviço.

## Continuidade e incidentes

- Manter procedimentos para indisponibilidade, vazamento, perda de dados, comprometimento de identidade e falha de fornecedor.
- Definir responsáveis, escalonamento, comunicação e preservação de evidências do incidente.
- Permitir desativar IA e integrações sem impedir operações essenciais quando possível.
- Documentar operação manual temporária para atividades críticas do cliente.
- Executar exercícios periódicos de restauração e resposta.

## Segurança operacional

- Acessos administrativos usarão identidade individual e MFA.
- Privilégios serão temporários e mínimos quando suportado.
- Vulnerabilidades e dependências terão monitoramento e política de correção.
- Ambientes serão protegidos contra exposição pública acidental.
- Atualizações relevantes produzirão trilha de auditoria.
- Testes de segurança precederão a entrada de dados reais.

## Alternativas consideradas

### Servidores administrados manualmente

Não preferidos para a fase inicial devido ao custo de correção, backup, alta disponibilidade e operação.

### Plataforma totalmente específica de um fornecedor

Não adotada como princípio. Serviços proprietários podem ser usados quando o benefício superar o custo de portabilidade e houver estratégia de saída.

### Produção e homologação na mesma fronteira

Rejeitada pelo risco de credenciais, mudanças e dados atravessarem ambientes.

### Backup sem exercícios de restauração

Rejeitado porque não oferece evidência suficiente de recuperabilidade.

## Consequências

### Positivas

- Menor carga operacional por uso criterioso de serviços gerenciados.
- Ambientes e mudanças reproduzíveis.
- Diagnóstico, segurança e recuperação incorporados desde o início.

### Negativas e riscos

- Serviços gerenciados podem aumentar custo e dependência do provedor.
- Observabilidade e continuidade exigem manutenção permanente.
- Metas excessivas de disponibilidade podem encarecer prematuramente o produto.

## Critérios para escolher a plataforma

- competência operacional já existente no ecossistema;
- regiões, privacidade e requisitos contratuais;
- serviços gerenciados para banco, objetos, filas e segredos;
- identidade, auditoria e isolamento de ambientes;
- observabilidade, backup e recuperação;
- custo previsível do piloto à expansão;
- portabilidade e procedimento de saída.

## Critérios para aceitação

- Inventariar a plataforma e as ferramentas reais do monorepo.
- Definir responsáveis operacionais e fluxo de mudanças.
- Aprovar diagrama de implantação e fronteiras de rede.
- Definir RPO, RTO e política de retenção.
- Restaurar banco e evidências em exercício documentado.
- Testar rollback, alerta crítico e indisponibilidade do provedor de IA.
- Aprovar checklist de produção antes do primeiro dado real.

## Confronto com o monorepo (aceite)

Decisões fechadas após inventário:

- **Nuvem preferencial:** AWS, competência já existente.
- **Região app/dados:** `us-east-2` (S3, SES, Cognito, RDS/ECS alinhados a inove).
- **Forma de implantação alvo:** ECS Fargate + ALB + RDS + Secrets Manager (padrão inove), não PM2 do Hub.
- **Async:** trabalhador do monólito + persistência de jobs no Postgres no MVP; broker gerenciado quando justificado.
- RPO/RTO numéricos e checklist de produção permanecem obrigatórios antes de dados reais.

## Referências

- NIST, Contingency Planning: https://csrc.nist.gov/Topics/Security-and-Privacy/security-programs-and-operations/contingency-planning
- NIST SP 800-34 Rev. 1: https://doi.org/10.6028/NIST.SP.800-34r1
- `ADR-005-banco-de-dados.md`
- `ADR-007-armazenamento-de-evidencias.md`
- `ADR-008-camada-e-governanca-de-ia.md`

