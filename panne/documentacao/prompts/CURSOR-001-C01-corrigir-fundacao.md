# CURSOR-001-C01 — Corrigir a fundação da Panne

## Objetivo

Corrija exclusivamente as divergências encontradas na revisão do `CURSOR-001`.

Não implemente funcionalidades novas e não avance para o banco de domínio.

## Correção 1 — Python 3.12

O projeto foi especificado para Python 3.12, mas foi configurado com:

```text
requires-python = ">=3.11"
```

Corrija a declaração para exigir Python 3.12 ou superior:

```text
requires-python = ">=3.12"
```

Revise também:

- documentação;
- scripts;
- comentários;
- configurações de ferramentas;
- eventuais arquivos de ambiente;
- metadados do projeto.

Todos devem indicar Python 3.12 como versão mínima oficial.

A estação atual possui somente Python 3.11.15. Não instale o Python 3.12 sem autorização e não altere a arquitetura para acomodar silenciosamente o runtime local.

Se não for possível executar novamente os testes com Python 3.12:

1. registre explicitamente a limitação;
2. informe quais validações permaneceram baseadas em Python 3.11;
3. não declare compatibilidade comprovada com Python 3.12;
4. preserve o alvo arquitetural mínimo em 3.12.

## Correção 2 — `.env.example`

Remova do `.env.example` qualquer senha, credencial ou valor que possa ser confundido com uma credencial real.

Use marcadores inequívocos, por exemplo:

```text
POSTGRES_USER=<configure-local-user>
POSTGRES_PASSWORD=<configure-local-password>
POSTGRES_DB=panne
```

Adapte os nomes às variáveis efetivamente utilizadas pela aplicação.

Se a execução local exigir os valores compartilhados pelo workspace:

- documente onde o desenvolvedor deve configurá-los localmente;
- não grave a senha no repositório;
- não altere nem exponha credenciais das outras aplicações.

Verifique o diff e os arquivos não rastreados da Panne para confirmar que nenhuma credencial real foi adicionada.

Não reproduza senhas no relatório de retorno. Informe somente se valores literais sensíveis foram encontrados e removidos.

## Atualização documental

Atualize:

- README da Panne;
- documentação da fundação;
- retorno da execução;
- histórico de prompts.

Registre este prompt integralmente em:

```text
documentacao/prompts/
```

Registre o retorno em arquivo separado.

## Restrições

- Não implemente tabelas de negócio.
- Não altere o modelo do banco.
- Não implemente autenticação.
- Não implemente módulos funcionais.
- Não integre IA.
- Não altere frontend ou backend fora do necessário para estas duas correções.
- Não modifique outras aplicações.
- Não faça commit, push ou deploy.
- Preserve todas as alterações preexistentes.

## Validações obrigatórias

Execute e registre:

1. busca por declarações incompatíveis de Python 3.11 na Panne;
2. confirmação de que o projeto exige Python 3.12 ou superior;
3. busca por credenciais literais nos arquivos criados ou alterados;
4. `git diff --check`;
5. `git diff --stat`;
6. `git status --short`.

Reexecute testes, lint, tipos e build apenas se as alterações realizadas puderem afetá-los. Caso não os execute novamente, justifique objetivamente.

## Retorno obrigatório

Entregue:

1. arquivos alterados;
2. declaração final da versão mínima do Python;
3. tratamento adotado para a indisponibilidade local do Python 3.12;
4. confirmação de que o `.env.example` não contém credenciais;
5. resultado da busca por credenciais nos arquivos da Panne;
6. validações executadas e resultados;
7. resumo de `git diff --stat` e `git status --short`;
8. confirmação de que nenhuma funcionalidade foi adicionada;
9. confirmação de que outras aplicações permaneceram intactas.

Não avance para o `CURSOR-002`. Aguarde a revisão do arquiteto.
