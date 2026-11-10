# ACTIONFINANCE — Prompt 065 · Aplicar o P03 (Início no uso real) e nomear os métodos de pagamento

## Regras
- Não alterar a Spider, a Loja nem o Hub. Sem mudança de banco.
- Testes: só os do Início (`HomePage.test.tsx`, `App.test.tsx`) e os do overview.

## Passos
0. **SSH:** atualizar a regra para o IP público atual (abrir a nova, testar, só então fechar a antiga).
1. **Aplicar o patch do Claude** na branch `feat/actionfinance-extrato-032`:
   `git am -3 "C:\Projetos\claude\2026-11-09-actionfinance-corporate-analyser\patches\P03-inicio-uso-real.patch"`
   - Base: `92ecd1a` (0.2.16). Só toca em `frontend/src` (HomePage e app.css).
   - Se houver conflito, parar e relatar.
2. **Backend, métodos de pagamento:** em "De onde veio o dinheiro", a venda com método `card` aparece como **"Outros"**. No overview, nomear em português os códigos conhecidos do Pay/Mercado Pago:
   - `pix` → Pix;
   - `card` → Cartão;
   - `credit_card` → Cartão de crédito;
   - `debit_card` → Cartão de débito;
   - `account_money` → Saldo Mercado Pago;
   - `ticket`/`bolbradesco` → Boleto.
   "Outros" fica só para código desconhecido, que deve ir para o log (apenas o código). Teste com `card`.
3. **Build e testes** da área.
4. **Publicar 0.2.17:** nova task web; retorno para `:33`.
5. **Verificar:** health 200 e `system/info` 0.2.17. O Oscar confere a tela.

## Entrega
- `documents/reviews/ACTIONFINANCE_REV_APLICAR_P03_065.md` (curto): o hash do patch, os métodos mapeados, a versão, a task e o retorno.
- Copiar este prompt para `documents/prompts/`. Commit, push e deploy.
