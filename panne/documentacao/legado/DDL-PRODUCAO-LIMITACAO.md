# Inventário DDL de produção (legado)

Ciclo: CURSOR-011.

## Acesso neste ciclo

A conexão MySQL segura **não estava disponível** no ambiente de execução:

- variáveis `PANNE_MYSQL`, `MYSQL_HOST`, `MYSQL_URL`, `LEGACY_MYSQL` ausentes no processo;
- nenhum processo `mysqld` visível nesta sessão;
- FTP não foi aberto.

**Não foram procuradas credenciais no computador.** Nenhuma sessão MySQL foi aberta. Nenhuma linha de negócio foi lida. Nenhuma escrita. Nenhuma exportação.

## O que já existe em `panne/documentacao/legado/`

Inventários estruturais dos ciclos 002–004 (metadados/`SHOW CREATE TABLE` à época):

- 80 tabelas no catálogo legado;
- núcleo documentado: empresa, usuário, produto, ingrediente, ficha, nutrição, medida;
- periferia citada **sem detalhe de produção**: `tbl_pop*` (POP/inspeção), `tbl_lancamento_docs` (financeiro), “planos e backups”;
- **nenhuma tabela de ordem de produção, batelada, quadro, pesagem ou apontamento** foi inventariada pelos nomes conhecidos.

## Inferência permitida (só do que já está escrito)

A ficha técnica legado (`tbl_ficha_tecnica` + linhas + modo de preparo + porção) é o artefato que hoje se imprime e se entrega ao padeiro. Não há, nesse núcleo:

- vínculo de uma emissão a uma ordem;
- snapshot imutável datado da impressão;
- batelada;
- planejado versus realizado;
- máquina de estados operacional;
- evento append-only de execução.

Se uma conexão somente leitura for reaberta em ciclo futuro, o inventário estrutural de produção deve completar este arquivo — ainda sem linhas de negócio.
