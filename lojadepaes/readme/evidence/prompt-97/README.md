# Prompt 97 — Entrar e Receber código (09/10/2026)

Correção isolada do login da Loja. Sem contratação, Mercado Pago, Pay, Agenda ou planos. Sem e-mail real, senha do proprietário ou contas novas em produção.

## Causa

O 95B já havia colocado Entrar, código e Receber código no popover. Ainda faltava:

1. E-mail e CPF apareciam juntos; Entrar exigia e-mail. CPF parecia segundo segredo — o proprietário colocou credencial administrativa ali.
2. Verificar só aceitava e-mail; quem se identificava por CPF não conseguia entrar só com documento + código.
3. O formulário administrativo existia no cabeçalho (Usuário / Senha) mas não se chamava **Acesso administrativo**. “Conta” é só o menu depois do login admin — não é terceira entrada de cliente.

## Fluxo final

### Cliente

Código temporário, 15 minutos, uso único. Sessão de 30 dias. Não é senha permanente.

1. Identifique-se.
2. Escolhe **E-mail** ou **CPF** (um só).
3. Preenche **Código de acesso** e **Entrar** — se já tiver código válido, não pede outro.
4. **Receber código** é a única ação que solicita envio, sempre ao e-mail cadastrado (mascarado). CPF não troca o destinatário.
5. Código inválido/expirado/consumido: mensagem clara, identificação preservada, sem envio automático.
6. Autenticado vê o resumo existente. Sem assinatura não inventa benefício. **Sair** reusa o logout da fidelidade.

### Administrador

Formulário próprio no cabeçalho (`#acesso`), agora com nome **Acesso administrativo**: Usuário e **Senha** mascarada. Também há o atalho no popover do cliente. Papel admin continua só no servidor. Sessões admin não foram invalidadas.

## Testes isolados (fictícios)

| Prova | Resultado |
|---|---|
| Entrar com código já emitido, sem novo outbox | ok |
| Entrar por CPF; e-mail estranho é ignorado | ok |
| Receber por CPF vai ao e-mail cadastrado | ok |
| Inválido / consumido / expirado | ok, sem enumerar CPF desconhecido |
| Limite de reenvio 60s | ok |
| UI: Entrar + Receber código sem envio ao abrir | ok |
| UI: erro preserva e-mail; autenticado sem assinatura + Sair | ok |
| Admin: formulário “Acesso administrativo”, senha mascarada | ok |

Frontend: 18 testes. Backend: `test_prompt97.py` + `test_prompt91g.py` — 12 passaram. Capturas isoladas: `captures/isolated-*.png`.

## Produção

Inspeção pública do popover apenas — sem Entrar, Receber código, senha ou conta do proprietário. Não afirma autenticação real.

## Publicado

| Peça | Versão |
|---|---|
| Loja | `lojadepaes:prod-20261009d` (rollback `prod-20261009c`) |
| Bundle | `/assets/index-Cv7pBd4W.js` + `index-CKkGPcs9.css` |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261009T124654Z.sql.gz` |
| Alembic | `d7e0f5a24b38` — sem migração nova |
| Hub / Pay / Agenda / Spider | intocados |

Hub 95B financeiro permanece como estava.
