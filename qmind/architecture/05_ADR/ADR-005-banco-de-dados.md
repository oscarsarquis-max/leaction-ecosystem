# ADR-005 — Banco de dados transacional

- Status: Aceito
- Aceito em: 2026-08-03
- Base de aceite: `../04_Docs/005_Monorepo_Confrontation.md`
- Data: 2026-08-03
- Responsáveis: equipe QMind

## Contexto

O núcleo do QMind possui relações fortes e auditáveis entre organizações, processos, avaliações, requisitos, evidências, constatações, ações e relatórios. Essas relações exigem integridade referencial, transações, consultas analíticas e evolução controlada do esquema. O isolamento lógico definido no ADR-002 também requer defesa consistente por organização.

## Decisão proposta

Adotar **PostgreSQL como banco transacional principal**, em instância e base logicamente pertencentes ao QMind. O uso de infraestrutura compartilhada do ecossistema somente será permitido após comprovar isolamento, capacidade, backup, responsabilidade operacional e ausência de acoplamento com outras aplicações.

O modelo inicial será relacional e normalizado conforme as invariantes do domínio. Colunas JSON poderão guardar extensões versionadas ou dados semiestruturados, mas não substituirão entidades centrais, chaves estrangeiras ou campos necessários para autorização e relatórios.

## Isolamento multiempresa

- Registros de negócio terão `organization_id` obrigatório.
- Chaves estrangeiras e restrições deverão impedir relações entre organizações diferentes.
- Unicidades locais incluirão `organization_id`.
- A aplicação sempre aplicará o contexto autorizado.
- Row-Level Security será avaliada e, se adotada, funcionará como defesa adicional com política padrão de negação.
- O papel usado pela aplicação não deverá ser superusuário, proprietário das tabelas nem possuir permissão de ignorar RLS.
- Testes automatizados deverão provar isolamento de leitura e escrita.

## Identificadores e tempo

- Entidades expostas externamente usarão identificadores não sequenciais adequados à stack escolhida.
- Datas técnicas serão armazenadas com fuso inequívoco e apresentadas no fuso do usuário ou da organização.
- Registros auditáveis terão criação e alteração, autoria e versão quando aplicável.
- Exclusão lógica só será usada quando existir razão regulatória ou de negócio; não será padrão universal.

## Migrações

- Toda alteração de esquema será versionada e revisada.
- Migrações deverão ser compatíveis com a estratégia de implantação e reversão.
- Alterações destrutivas exigirão backup verificado e plano de transição.
- Dados de referência e dados de demonstração serão separados.
- Nenhuma migração poderá copiar dados reais entre organizações ou ambientes.

## Auditoria

O histórico de negócio não será inferido apenas de logs técnicos. Eventos relevantes — aprovação de constatação, publicação de relatório, alteração de responsável, mudança de prazo e acesso administrativo — terão registro próprio, com ator, organização, ação, recurso, data e correlação.

## Busca e dados vetoriais

Busca textual nativa poderá atender a primeira versão. Índices vetoriais serão introduzidos apenas quando casos de recuperação semântica forem validados. Qualquer índice derivado deverá manter organização, origem, versão, permissões e mecanismo de reconstrução.

## Alternativas consideradas

### Reutilizar automaticamente o banco de outra aplicação

Rejeitado. Existência prévia não demonstra compatibilidade, propriedade operacional ou isolamento adequado.

### Banco orientado a documentos como fonte principal

Não adotado porque o domínio exige integridade relacional e rastreabilidade entre muitas entidades.

### Banco separado por cliente desde o início

Não adotado como padrão inicial devido ao custo operacional. Continua possível para contratos especiais mediante novo ADR.

## Consequências

### Positivas

- Integridade transacional e referencial.
- Ecossistema maduro de ferramentas e operação.
- Suporte a consultas relacionais, documentos auxiliares e busca textual.
- Possibilidade de RLS como defesa adicional.

### Negativas e riscos

- RLS possui exceções e detalhes operacionais; não elimina autorização na aplicação.
- Migrações exigem disciplina conforme o produto cresce.
- Uso excessivo de JSON pode degradar o modelo e a qualidade dos relatórios.

## Confronto com o monorepo (aceite)

Decisões fechadas após inventário:

- **Motor:** PostgreSQL 18 no container `leaction_db` (local). Porta host vigente no compose: **5434** (documentação legada ainda cita 5433).
- **Base lógica:** `qmind` (dedicada; provisionar em `infra/ecosystem-databases.sql` e sync LAN quando a implementação começar).
- **Migrações:** SQL versionado no estilo inove (`qmind/.../migrations/NNN_*.sql` + `.down.sql` quando fizer sentido).
- **IDs externos:** UUID (não serial exposto).
- Propriedade operacional, backup e RPO/RTO seguem ADR-009; modelo conceitual precede o esquema físico (`02_Models`).

## Referências

- PostgreSQL, Row Security Policies: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- `ADR-002-isolamento-multiempresa.md`
- `ADR-003-backend-e-contrato-api.md`

