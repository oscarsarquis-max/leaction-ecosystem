# PRM_007 — Adendo 003: correção de caracteres no nome da empresa

Data: 30/09/2026. Analista → Cursor. Mesmo ciclo PRM_007, sem PRM_008.

## Defeito observado pelo proprietário

No cabeçalho público de `/receivables`, o nome aparece como **“Loja de PÃ£es”**. O valor correto confirmado é **“Loja de Pães”**. A imagem demonstra corrupção de caracteres, mas não determina sozinha se o erro está no valor persistido, na serialização ou na leitura da resposta.

Corrigir o defeito e sua origem dentro do PRM_007. Não remover acentos nem aplicar substituição visual genérica. Não reabrir arquitetura, ingresso, identidade visual ou regras financeiras.

## Diagnóstico e correção

1. Rastrear o nome pelo comando/bootstrap real de produção, valor no PostgreSQL, resposta JSON do acesso/contexto e renderização. Conferir caracteres Unicode/bytes de forma objetiva, sem confiar apenas na aparência do terminal. Não imprimir segredos ou dados financeiros.
2. Conferir script/JSON de provisionamento, codificação de arquivos, passagem de argumentos entre PowerShell/CLI/container/Java, conexão PostgreSQL e headers/decodificação HTTP. Identificar o primeiro ponto em que `ã` deixa de ser U+00E3. Não atribuir a causa ao banco ou ao browser sem evidência.
3. Se o valor já estiver incorreto no banco, reparar somente os nomes de exibição efetivamente afetados da Loja de Pães, por comando administrativo apropriado ou transação parametrizada e restrita aos IDs confirmados. Registrar antes/depois, motivo e operador em auditoria compatível. Preservar IDs, códigos, vínculos, login, permissões e todos os fatos financeiros. Conferir quantidade exata de linhas; nenhuma substituição global ou recodificação indiscriminada de tabelas. Não alterar migrations já aplicadas.
4. Se o banco estiver correto, corrigir a camada que corrompe a resposta sem regravar o dado íntegro. Em qualquer caso, corrigir também o caminho responsável para que novos cadastros com acentos não repitam o defeito.
5. Usar UTF-8 de ponta a ponta conforme o caminho diagnosticado. Não tratar apenas `$OutputEncoding` ou `Set-Content` como cura presumida: comprovar transporte real do texto. Não duplamente decodificar JSON ou usar replace de `Ã` na interface.

## Provas e entrega

- No ensaio isolado, passar pelo mesmo caminho de cadastro afetado com texto como `Padaria São João — Ação e Pães`; conferir persistência, API e tela. Não criar empresa fictícia no banco de produção para esse teste.
- No destino real, comprovar `Loja de Pães` na API e no cabeçalho após atualização da sessão/página. Confirmar que ator e empresa mantêm seus IDs. Guardar captura sem tokens/cookies.
- Executar testes proporcionais à mudança. Se houver alteração de código/artefato, reconstruir, implantar pela rotina existente e registrar digest final; se apenas script/dado administrativo mudar, não fazer deploy desnecessário.
- Registrar causa, correção, quantidade de registros afetados, evidências e necessidade ou não de nova imagem em adendo do REV_007. Copiar este texto para documents/prompts e indexar.

O problema visual não comprova, por si só, os gates ainda pendentes de login/logout/CSRF e restore remoto. Continuar essas verificações do PRM_007 sem pedir senha/MFA pelo chat. Não declarar publicação concluída enquanto faltarem provas.
