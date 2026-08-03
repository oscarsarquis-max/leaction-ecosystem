# ADR-003 — Backend e contrato de API

- Status: Aceito
- Aceito em: 2026-08-03
- Base de aceite: `../04_Docs/005_Monorepo_Confrontation.md`
- Data: 2026-08-03
- Responsáveis: equipe QMind

## Contexto

O QMind terá interfaces web e possivelmente móvel, processos assíncronos e futuras integrações. Todos esses consumidores precisam acessar os mesmos casos de uso sem duplicar regras de negócio. A API deverá preservar isolamento multiempresa, rastreabilidade e evolução controlada.

A linguagem e o framework do backend ainda dependem do inventário do monorepo. Este ADR define o estilo e as obrigações do contrato antes da escolha tecnológica.

## Decisão proposta

Adotar uma **API HTTP orientada a recursos e casos de uso**, documentada por contrato e servida pelo monólito modular definido no ADR-001.

REST será o estilo inicial para operações síncronas. Tarefas demoradas serão representadas como recursos de processamento assíncrono, com estado consultável. Eventos internos não serão expostos como contrato público por padrão.

## Regras do contrato

### Recursos e rotas

- URLs representam recursos do domínio e não nomes de telas.
- Operações de negócio que não sejam CRUD simples terão comandos explícitos e restritos.
- Recursos pertencentes a cliente serão sempre resolvidos no contexto da organização autenticada.
- O cliente não poderá elevar ou trocar o contexto organizacional apenas enviando `organization_id`.
- Datas e horários usarão formato ISO 8601 e serão persistidos com referência temporal inequívoca.

### Entradas e saídas

- Entradas terão validação estrutural e semântica.
- Saídas não exporão entidades de persistência diretamente.
- Enumerações e estados de fluxo serão documentados.
- Valores calculados deverão informar versão ou critério quando isso afetar sua interpretação.
- Conteúdo gerado por IA indicará estado de revisão e referências disponíveis.

### Erros

Erros usarão uma estrutura uniforme contendo, no mínimo:

- código estável legível por máquina;
- mensagem segura para o usuário;
- identificador de correlação;
- detalhes de campos quando aplicável.

Respostas não deverão revelar detalhes internos, consultas, caminhos, credenciais ou dados de outra organização.

### Concorrência e idempotência

- Atualizações críticas usarão controle de versão para detectar edição concorrente.
- Comandos que possam ser repetidos por falha de rede aceitarão chave de idempotência quando necessário.
- Repetições não poderão duplicar ações, relatórios, uploads ou cobranças futuras.

### Paginação e filtros

- Coleções potencialmente grandes serão paginadas.
- Filtros e ordenações permitidos serão explícitos.
- A paginação não poderá vazar contagens ou itens de outra organização.
- Exportações grandes serão executadas de forma assíncrona.

### Versionamento

- O contrato terá uma versão principal explícita.
- Mudanças compatíveis serão preferidas dentro da mesma versão.
- Remoções e mudanças incompatíveis exigirão período de transição e versão nova.
- Contratos publicados serão verificados automaticamente em integração contínua.

## Processamentos assíncronos

Geração de relatórios, análise de documentos e tarefas de IA poderão retornar um recurso de trabalho contendo estado, progresso quando disponível e resultado ou erro final.

Estados mínimos sugeridos:

```text
queued -> running -> succeeded
                 -> failed
                 -> cancelled
```

Todo trabalho deverá preservar organização, solicitante, correlação, versão do comando e política de repetição.

## Segurança

- Autenticação e autorização serão aplicadas antes do caso de uso.
- O caso de uso ainda validará permissões e invariantes relevantes.
- Limites de tamanho, tipo de arquivo e frequência serão definidos por operação.
- Operações sensíveis gerarão eventos de auditoria.
- Segredos nunca serão enviados ao cliente.
- Proteções contra requisições forjadas, abuso e enumeração serão adequadas ao mecanismo de autenticação escolhido.

## Documentação e testes

- O contrato deverá ser gerado ou validado a partir de uma especificação legível por máquina.
- Exemplos não conterão dados reais ou sensíveis.
- Testes cobrirão contrato, autorização, isolamento multiempresa e compatibilidade.
- Um fluxo completo de diagnóstico servirá como teste de aceitação transversal.

## Alternativas consideradas

### GraphQL como contrato inicial único

Não adotado inicialmente. Pode ser reconsiderado se necessidades reais de composição e múltiplos consumidores superarem o custo adicional de autorização, cache e governança de consultas.

### RPC sem especificação pública

Rejeitado porque dificultaria descoberta, compatibilidade e integrações futuras.

### Backend separado para cada interface

Não adotado no início. Camadas específicas para experiência podem ser introduzidas caso web e móvel desenvolvam necessidades substancialmente diferentes.

## Consequências

### Positivas

- Contrato previsível para diferentes consumidores.
- Regras de negócio permanecem centralizadas.
- Boa compatibilidade com documentação e ferramentas comuns.
- Evolução controlada por testes de contrato.

### Negativas e riscos

- Algumas operações de domínio exigirão modelagem cuidadosa para não degenerar em CRUD genérico.
- Versionamento e compatibilidade adicionam disciplina ao desenvolvimento.
- Tarefas assíncronas exigem persistência de estado e tratamento de repetição.

## Critérios para escolher linguagem e framework

- compatibilidade com o monorepo e competência da equipe;
- suporte maduro a validação, contratos e testes;
- segurança, manutenção e ciclo de suporte;
- integração com banco, filas, armazenamento e provedores de IA;
- observabilidade e desempenho compatíveis com o produto;
- custo operacional e facilidade de contratação.

## Confronto com o monorepo (aceite)

Decisões fechadas após inventário:

- **Stack:** Python **FastAPI** (OpenAPI nativo; precedente em `phanton`; melhor aderência a contrato testável do que Flask/Express do Hub).
- **Prefixo público:** `/api/v1`.
- **Contrato:** especificação OpenAPI gerada/validada na CI do QMind (não existe padrão monorepo — será introduzido no app).
- **Async MVP:** tabela de trabalhos / outbox em PostgreSQL + processo trabalhador do mesmo código-base (padrão próximo ao outbox do Hub). Fila gerenciada (ex.: SQS) exige revisão quando volume ou isolamento operacional justificarem.
- Integrações públicas no MVP: não previstas; API autenticada para o produto.

## Referências internas

- `ADR-001-arquitetura-modular.md`
- `ADR-002-isolamento-multiempresa.md`

