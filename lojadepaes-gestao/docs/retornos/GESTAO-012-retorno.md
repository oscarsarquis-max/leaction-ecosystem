# GESTAO-012 — Gigio no editor de receita

Base: `feat/gestao-011-importar` (`87139706`). Branch: `feat/gestao-012-gigio`. Imagem em produção: `lojadepaes-gestao:012-20261106` (anterior: `011-20261106`).

O padeiro sabe os números-base e não mede as inclusões com precisão. O Gigio sugere. O padeiro decide. Nada é publicado sozinho.

## 0. Referência da Loja

`docs/GIGIO-REFERENCIA.md`. Leitura só do código em `C:\Projetos\lojadepaes`. Nenhum arquivo, contêiner ou `.env` da Loja foi alterado. A credencial da Loja não foi lida.

O modelo e a região saem de `bedrock_model_id` / `BEDROCK_MODEL_ID` e `bedrock_region` / `BEDROCK_REGION`, com as constantes `CHAMELLEON_BEDROCK_MODEL_ID` e `CHAMELLEON_BEDROCK_REGION` quando os dois estão vazios. Este retorno não grava o valor dessas constantes. A chamada é `invoke_model`.

O avatar copiado é `frontend/public/avatar_gigio.png`. SHA-256 igual ao original `frontend/images/logos/avatar_gigio.png`: `c9c87b87dcb16a6ed90cfbe381e257af8ca6c92fa29c01c7cd5584f2b2a89c8b`.

## 1. Padrões da casa

Tabela `padrao_padaria`, por organização. A migração `0008_gigio` planta cinco sementes em cada organização que já existia. Organização nova também recebe as cinco, no `criar-organizacao`.

| Nome | Termo | % |
|---|---|---|
| Hidratação | água | 60 |
| Água residual do fermento | água residual do fermento | 6, além da hidratação |
| Leite em pó ou farinha láctea | leite em pó | 10 |
| Levain | levain | 20 |
| PFF | PFF | 20 |

A tela é Gestão › Padrões. A lista segue o padrão das outras, e a edição é o painel único. No Gigio, o padrão ativo entra como regra da casa. Linha fixa vale mais que o padrão.

## 2. Sugestão

`POST /receitas/{produto_id}/sugestao-gigio` não grava a receita. `POST /receitas/{produto_id}/aplicar-sugestao` grava o rascunho e não publica.

A entrada leva produto, família, descrição, massa-base, linhas fixas, rendimento e os nomes e categorias dos ingredientes. Não leva custo, preço nem dado pessoal. A saída é a ferramenta `sugerir_receita`: linhas com quantidade, %, faixa, confiança e motivo, mais rendimento, perda, modo de fazer e observações.

O ingrediente passa pela busca que já existia. Sem destaque, ou só no catálogo, fica "a decidir". Nenhum ingrediente é criado. Limite: 30 sugestões por dia por organização, 30 segundos. Sem credencial o botão fica desligado.

`receita_linha.origem`: `manual`, `estimado` ou `conferido`. A linha aplicada da sugestão entra `estimado`. Mudar a quantidade, ou "Marcar como conferido", passa a `conferido`. A faixa fica na linha para o mouse.

A auditoria `gigio_sugestao` guarda quem pediu, quando, o modelo, os tokens, a entrada e a saída.

## 3. Migração

`pg_dump -Fc` do banco `gestao` **antes** do Alembic: `/opt/lojadepaes-gestao/backups/gestao-pre012.dump` (91.885 bytes, SHA-256 `afd68a7cf0b5d883b7eca58fd1fb3d830490ab60f1275be8f24587e94e2d7594`, `chmod 600`). `pg_restore --list`: 184 linhas. Antes do dump: `alembic_version = 0007_importacao_loja`, uma organização (`boulangerie`).

Alembic `0007_importacao_loja` → `0008_gigio`. Só acrescenta `receita_linhas.origem` (nasce `manual`), `faixa_min`, `faixa_max`, `padrao_padaria` e `gigio_sugestao`. `carregar-catalogo` não rodou.

## 4. Testes

| Onde | Resultado |
|---|---|
| `pytest` no backend | **257 passed** |
| `pytest tests/test_gigio.py`, depois de alinhar o gateway falso à hidratação de 60 % | **7 passed** |
| `vitest` no frontend | **83 passed** |
| `ruff` | limpo |

O arquivo novo cobre: linha fixa e massa-base intocadas; "fermento seco" não liga a "fresco"; desconhecido fica "a decidir" e nenhum ingrediente nasce; aplicar cria `estimado` e mudar a quantidade vira `conferido`; a receita continua rascunho; sem credencial, 503; a 31ª sugestão do dia, 429; a auditoria não tem custo nem preço; a outra organização não vê a sugestão; as cinco sementes existem e o Levain editado vai a 25 %.

## 5. Capturas locais

`scripts/capture-gestao-012.mjs`, com `GESTAO_GIGIO_GATEWAY=fake`, em `docs/evidence/gestao-012-local/`. Checagem em `capturas.md`: sem rolagem horizontal e controles de 40 px (44 abaixo de 960). O exemplo é o Pão de Canela sobre a Massa sovada.

| O que mostra | 320 | 390 | 768 | 960 | 1280 | 1440 |
|---|---|---|---|---|---|---|
| Passo 1 | `gigio-passo1-320.png` | `gigio-passo1-390.png` | `gigio-passo1-768.png` | `gigio-passo1-960.png` | `gigio-passo1-1280.png` | `gigio-passo1-1440.png` |
| Passo 3 | `gigio-passo3-320.png` | `gigio-passo3-390.png` | `gigio-passo3-768.png` | `gigio-passo3-960.png` | `gigio-passo3-1280.png` | `gigio-passo3-1440.png` |
| Receita com estimado | `receita-estimado-320.png` | `receita-estimado-390.png` | `receita-estimado-768.png` | `receita-estimado-960.png` | `receita-estimado-1280.png` | `receita-estimado-1440.png` |

## 6. Publicação

- Antes: 906 MB de memória disponíveis, 19,8 GB livres. Imagem no ar: `011-20261106`.
- Usuário IAM `gestao-gigio`, sem política gerenciada anexada. A política inline `gestao-gigio-invoke` permite só `bedrock:InvokeModel`, no perfil de inferência da conta e nos três modelos de fundação para onde esse perfil encaminha (`us-east-1`, `us-east-2`, `us-west-2`).
- `/etc/gestao/gigio.env` é `root` e modo `600`. A sessão `ubuntu` não lê o arquivo. O `gestao-api` recebe as variáveis no arranque. O compose de produção passou a ter esse segundo `env_file`.
- SSH: porta 22 aberta **só para o meu IP /32** (`191.57.244.103`; não estava entre as 29) e **fechada em seguida**. Voltou a 29 regras. 80 e 443 seguem em `0.0.0.0/0`. Chave temporária, o tar e a cópia local da credencial foram removidos.
- Dump acima, depois `alembic upgrade head` **somente**.
- `gestao-api` recriado e saudável com `lojadepaes-gestao:012-20261106`. Health e ready 200.
- O JavaScript servido (`index-DVnY5DjO.js`) tem o mesmo SHA-256 do build local, da imagem e do ar (`1308a27eef59ec892d0e4f745cb5bf10983c715fe7c6e386b7f3d6691021ae66`).
- **Uma** sugestão real, na organização `gigio-teste`, produto "Pão de teste do Gigio". Auditoria `9698b10e-50d6-4119-9104-ec5f41aa2f77`, modelo o mesmo da Loja, 1388 tokens de entrada e 481 de saída, três linhas (Farinha, Água, Canela). A entrada gravada não tem chave de custo, preço ou dado pessoal. A sugestão não foi aplicada e não foi publicada. `boulangerie` tem 0 sugestões e as 5 sementes. `gigio-teste` tem 1 sugestão e as 5 sementes.
- **`https://lojadepaes.com.br/` 200**, `https://gestao.lojadepaes.com.br/` 200. `pg_stat_user_tables` da Loja igual antes e depois: `media_assets` 16/0/0, `product_variants` 16/6/6, `products` 16/35/6, `showcase_slots` 10/16/0.

## 7. Rollback

A imagem `011-20261106` continua no host. Recolocar `GESTAO_IMAGE=lojadepaes-gestao:011-20261106` e recriar só o `gestao-api`. A cópia anterior do compose está em `deploy/docker-compose.prod.yml.bak011`. As tabelas novas podem ficar: a imagem anterior não as usa. O dump `gestao-pre012.dump` está no host se for preciso voltar o banco.

## Checklist

1. **Feito.** `docs/GIGIO-REFERENCIA.md` cita modelo e região pelo nome da variável e da constante. Nenhum segredo.
2. **Feito.** Avatar com o mesmo SHA-256 do original da Loja.
3. **Feito.** 257 testes do backend, 7 do Gigio de novo depois do ajuste do falso, 83 do frontend, ruff limpo.
4. **Feito.** Passo 1, passo 3 e a receita com "estimado", nas seis larguras, Pão de Canela sobre a massa sovada, com o gateway falso.
5. **Feito.** IAM `gestao-gigio` só com `InvokeModel`. `gigio.env` em 600. Uma sugestão real em `gigio-teste`. Boulangerie sem sugestão. `lojadepaes.com.br` 200. Loja intocada.
6. **Feito.** Este retorno e as capturas estão no mesmo commit, com push da branch.
