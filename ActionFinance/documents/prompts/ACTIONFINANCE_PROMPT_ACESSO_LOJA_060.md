# ACTIONFINANCE — Prompt 060 · Reenviar o acesso da Loja de Pães ao Oscar

## Objetivo
O Oscar não lembra o usuário com que entra no ActionFinance como Loja de Pães. Reenviar o acesso para **oscar@oscarsarquis.com.br**. Aproveitar para identificar a segunda empresa que falha no ciclo do 057.

## Regras
- Mexer só no **User Pool do ActionFinance** (Cognito, us-east-2) e, se preciso, no vínculo usuário ↔ empresa do próprio Finance. Não tocar na Spider, na Loja, no Hub nem em outros pools (`spider-prod-monitor` etc.).
- Não registrar senhas, códigos ou tokens no relato nem no terminal compartilhado.
- Não apagar nem desativar nenhum usuário.
- Sem deploy, sem testes.

## Passos
1. **Levantar (só leitura):**
   - empresas cadastradas no Finance: nome, CNPJ, integração Pay ativa ou não, resultado do último ciclo;
   - usuários do pool do Finance vinculados a cada empresa: username, e-mail, status no Cognito e permissões no Finance.
2. **Acesso da Loja de Pães:**
   - **Se já existe usuário com oscar@oscarsarquis.com.br** vinculado à Loja de Pães: `admin-reset-user-password`, para o Cognito enviar o código de redefinição a esse e-mail.
   - **Se existe usuário da Loja com outro e-mail:** não alterar o e-mail dele. Registrar no relato e seguir para o caso abaixo.
   - **Se não existe usuário com esse e-mail:** criar com `admin-create-user`, com o e-mail como atributo verificado e envio do convite com senha temporária. Vincular à empresa Loja de Pães com permissão de dono (leitura e escrita), do mesmo jeito que o vínculo atual é feito.
3. **Confirmar** que o e-mail saiu: status `FORCE_CHANGE_PASSWORD` ou `RESET_REQUIRED` e evento no CloudTrail/Cognito.

## Entrega
`documents/reviews/ACTIONFINANCE_REV_ACESSO_LOJA_060.md`, contendo:
- a tabela de empresas (nome, CNPJ, Pay ativo, último ciclo);
- a tabela de usuários (username, e-mail, empresa, status, permissões);
- o que foi feito para oscar@oscarsarquis.com.br e o **username** que ele deve usar no login;
- qual é a empresa que falha no ciclo e se ela parece de teste ou real (só a observação, sem mudar nada nela).

Copiar este prompt para `documents/prompts/`. Commit e push só dos dois arquivos.

## Aceite
O e-mail de acesso foi enviado para oscar@oscarsarquis.com.br, o username está no relato, nada foi apagado e a segunda empresa foi identificada.
