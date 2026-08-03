# ADR-007 — Armazenamento e proteção de evidências

- Status: Aceito
- Aceito em: 2026-08-03
- Base de aceite: `../04_Docs/005_Monorepo_Confrontation.md`
- Data: 2026-08-03
- Responsáveis: equipe QMind

## Contexto

Evidências podem incluir documentos, imagens, registros, atas e outros arquivos. Elas podem conter dados pessoais, propriedade intelectual e informações estratégicas. O banco transacional não é o local adequado para armazenar grandes binários, mas deve preservar metadados, vínculos, integridade e autorização.

## Decisão proposta

Armazenar arquivos em **serviço de objetos privado** e manter no PostgreSQL os metadados e relacionamentos de negócio.

Após confronto com o monorepo: **Amazon S3** em bucket **dedicado ao QMind** (privado), região **`us-east-2`**, acessado apenas por porta/adaptador do domínio — sem reutilizar o bucket CMS do Hub.

## Metadados mínimos

- identificador e organização proprietária;
- nome original sanitizado e nome/chave interna;
- tipo declarado e tipo detectado;
- tamanho e hash criptográfico;
- autor, origem e data de inclusão;
- classificação e política de retenção;
- estado de verificação de segurança;
- versão, substituições e vínculos de domínio;
- estado de processamento ou extração;
- data e motivo de exclusão quando aplicável.

## Fluxo de upload

1. O backend autoriza a intenção de upload.
2. O sistema cria registro pendente e destino restrito à organização.
3. O cliente envia o arquivo por mecanismo temporário e limitado.
4. O serviço valida tamanho, assinatura real do tipo e hash.
5. O arquivo permanece em quarentena até a verificação de segurança.
6. Somente arquivos aprovados ficam disponíveis aos fluxos de negócio.
7. Falhas, expiração e abandono produzem limpeza rastreável.

## Controles obrigatórios

- Recipientes e objetos serão privados por padrão.
- Chaves não usarão nomes fornecidos pelo usuário como identificador confiável.
- Links de acesso terão curta duração e serão emitidos após autorização.
- O acesso deverá ser revalidado; conhecer uma URL ou chave não concede permissão.
- Tipos, tamanhos e quantidades serão limitados por caso de uso.
- Arquivos executáveis ou perigosos serão bloqueados conforme política.
- Conteúdo ativo terá visualização isolada ou conversão segura quando necessário.
- Criptografia em trânsito e em repouso será obrigatória.
- Ações sensíveis de upload, download, substituição e remoção serão auditadas.

## Imutabilidade e versões

Uma evidência já usada em constatação ou relatório publicado não deverá ser sobrescrita. Correções criarão nova versão e preservarão o vínculo histórico. O hash permitirá detectar alteração ou corrupção, mas não substituirá cadeia de custódia e controle de acesso.

## Retenção e descarte

- A retenção será definida por categoria, contrato e obrigação aplicável.
- Bloqueio de exclusão poderá ser usado quando houver investigação ou obrigação de preservação.
- Exclusão lógica não bastará para cumprir descarte definitivo; objetos, derivados, caches e índices deverão entrar no fluxo de remoção.
- Backups seguirão prazos documentados e expiração controlada.
- O descarte produzirá registro sem conservar o conteúdo eliminado.

## Extração, busca e IA

- Processamento ocorrerá apenas após verificação de segurança.
- Texto extraído e fragmentos herdarão organização, classificação e retenção.
- Índices serão reconstruíveis a partir da fonte autorizada.
- Apenas conteúdo permitido será enviado a provedores de IA.
- Resultados derivados manterão ligação com arquivo, versão e páginas ou trechos quando possível.

## Alternativas consideradas

### Binários no banco relacional

Não adotado como padrão devido ao impacto em backup, desempenho e escalabilidade. Pequenos artefatos internos poderão ser exceção justificada.

### Pasta compartilhada como repositório definitivo

Rejeitada por dificultar autorização granular, versionamento, auditoria, integridade e operação SaaS.

### Objetos públicos com URLs difíceis de adivinhar

Rejeitados. Imprevisibilidade de URL não é controle de autorização.

## Consequências

### Positivas

- Escala e custo adequados a binários.
- Separação entre conteúdo e metadados transacionais.
- Possibilidade de quarentena, versionamento e links temporários.

### Negativas e riscos

- Consistência entre banco e objetos requer processos compensatórios.
- Verificação, extração e descarte introduzem tarefas assíncronas.
- O provedor escolhido pode afetar residência de dados e custos de saída.

## Critérios para escolher o provedor

- integração e suporte no ambiente do monorepo;
- isolamento, criptografia e gestão de chaves;
- versionamento, retenção e bloqueio quando necessários;
- região, disponibilidade, durabilidade e recuperação;
- auditoria, malware scanning e eventos;
- custo de armazenamento, operações e transferência;
- portabilidade por API e processo de exportação.

## Critérios para aceitação

- Validar upload, quarentena, download autorizado e exclusão.
- Testar acesso cruzado entre duas organizações.
- Simular arquivo malicioso, tipo falso, duplicado e upload abandonado.
- Demonstrar vínculo imutável de evidência com relatório publicado.
- Aprovar política inicial de classificação e retenção.

## Confronto com o monorepo (aceite)

Precedente S3 existe para CMS do Hub e não cobre custódia de evidências. QMind mantém bucket próprio, metadados no Postgres e fluxo de quarentena. Scanner de malware concreto será escolhido na implementação sem alterar este ADR.

## Referências internas

- `ADR-002-isolamento-multiempresa.md`
- `ADR-003-backend-e-contrato-api.md`
- `ADR-005-banco-de-dados.md`

