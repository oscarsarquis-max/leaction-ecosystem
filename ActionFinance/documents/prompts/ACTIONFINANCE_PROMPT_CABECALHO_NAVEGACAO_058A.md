# ACTIONFINANCE — Prompt 058A · Cabeçalho com CNPJ e nova navegação (retomada do 058)

O 058 parou no meio e nada foi commitado. Este prompt fecha **só** o cabeçalho, a navegação e o login. A tela Início fica para o 058B. Desenho: `documents/ux/desenho-001/` (se a pasta não estiver lá, copiar de `C:\Projetos\claude\2026-11-09-actionfinance-corporate-analyser\desenho-001\`).

## Regras
- Não alterar a Spider, a Loja nem o Hub.
- Testes: só os do shell e da migração. Não rodar a suíte inteira.
- Manter o código já feito do `GET /api/v1/overview` **sem commitar** (fica para o 058B). Usar `git stash` ou uma branch local, mas não publicar.

## Passos
0. **SSH:** atualizar a regra para o IP público atual (abrir a nova, testar, só então fechar a antiga).
1. **CNPJ no banco:**
   - Migração **V27**: só a coluna de CNPJ na empresa, opcional, texto de 14 dígitos (sem máscara), sem nenhum dado de cliente dentro do script.
   - O CNPJ da Loja de Pães (`69423547000104`) entra **depois** da V27, com um `UPDATE` único e registrado no relato, só se o Oscar tiver confirmado o número.
2. **Cabeçalho** igual ao desenho:
   - faixa `#1800AD` (token `--brand-mark`) e logo `af-logo-azul.png`, 40 px no desktop e 28 px no celular;
   - à direita, nome da empresa e, embaixo, "CNPJ 69.423.547/0001-04" com máscara. Sem CNPJ: "CNPJ não informado";
   - depois, usuário e Sair.
3. **Navegação:** Início · Caixa · Vendas · Pagamentos · Bancos · Cadastros, com os submenus:
   - Caixa: Resumo, Agenda;
   - Vendas: A receber, Recebimentos integrados;
   - Pagamentos: A pagar;
   - Bancos: Contas, Extratos, Conciliação;
   - Cadastros: como hoje.
   Nenhuma tela pode se perder. Enquanto o 058B não sai, **Início** mostra uma página simples com o título "Início" e o texto "Em breve: a leitura do mês da sua loja.", e o **login abre no Início**.
4. **Testes:**
   - o CNPJ aparece com máscara, e o texto "não informado" aparece quando falta;
   - cada tela antiga é alcançável pelo novo menu;
   - o login cai no Início.
5. **Publicar 0.2.13:**
   - snapshot `actionfinance-pre-v27-<data>`, task de migração (Flyway continua desligado na web) e o `UPDATE` do CNPJ;
   - nova task web; retorno para `:29` (reverter não remove a coluna).
6. **Verificar:** capturas do cabeçalho e do menu em 1440 e 390 com a sessão do Oscar, só leitura.

## Entrega
- `documents/reviews/ACTIONFINANCE_REV_CABECALHO_NAVEGACAO_058A.md`, com: versão, task, V27, `UPDATE`, retorno, testes e capturas.
- Copiar este prompt para `documents/prompts/`. Commit, push e deploy.

## Aceite
CNPJ visível em todas as telas, menu novo sem perder nenhuma tela, login no Início e a 0.2.13 no ar.
