# ACTIONFINANCE — Prompt 058B · Tela Início do dono

**Rodar depois do 058A.** Desenho: `documents/ux/desenho-001/Main.dc.html` (desktop) e `Mobile.dc.html` (celular). A tela deve ficar **igual ao desenho**.

## Regras
- Não alterar a Spider, a Loja nem o Hub. Sem mudança de banco.
- Todo número vem só da empresa da sessão.
- **Ausência não é zero:** fonte inexistente ou sem dados mostra "Não conectado" ou "Não apurado", nunca R$ 0,00.
- Testes: só os do overview e da tela Início.

## Passos
0. **SSH:** atualizar a regra para o IP público atual (abrir a nova, testar, só então fechar a antiga).
1. **Retomar o `GET /api/v1/overview`** já começado (stash ou branch local do 058) e conferir que entrega:
   - **Vendas:** valor pago dos recebimentos integrados no período, por método;
   - **Taxas:** tarifas do extrato importado; sem extrato, `nao_apurado`;
   - **Custos de produção:** `nao_conectado`;
   - **Despesas:** baixas de pagamentos, por categoria;
   - **Sobrou:** só com todas as partes apuradas; senão, valor parcial com a lista do que falta;
   - **Caixa de 8 semanas:** posição gerencial mais os títulos em aberto por semana de vencimento, com a menor semana marcada;
   - **Atenção:** no máximo 5 itens, por ordem de urgência:
     - pagamento que vence em até 2 dias;
     - título vencido;
     - ocorrências do extrato em revisão;
     - pendências de conciliação;
     - sincronização do Pay há mais de 2 h;
   - **Horário** da última sincronização e do último extrato.
2. **Tela Início** no lugar da página provisória do 058A:
   - **Leitura do mês** com frases fixas montadas a partir dos números (sem IA);
   - os 5 números e o gráfico de 8 semanas;
   - "Pede sua atenção", com cada item levando à tela certa;
   - "De onde veio", "Para onde foi" e a faixa da conta bancária;
   - celular igual ao `Mobile.dc.html`.
3. **Testes:**
   - o cálculo de cada bloco;
   - uma segunda empresa nunca aparece no resultado;
   - ausência ≠ zero;
   - Sobrou parcial.
4. **Publicar 0.2.14:** nova task web; retorno para a task do 058A.
5. **Verificar:** capturas do Início em 1440 e 390 com a sessão do Oscar, só leitura, comparadas lado a lado com o desenho.

## Entrega
- `documents/reviews/ACTIONFINANCE_REV_INICIO_058B.md`, com: versão, task, retorno, testes, capturas e as diferenças em relação ao desenho.
- Copiar este prompt para `documents/prompts/`. Commit, push e deploy.

## Aceite
Início igual ao desenho, números isolados por empresa e nenhum zero inventado.
