# SEGSENSE_DEMO_RUN_001 — Roteiro de 5 minutos (reunião local)

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_DEMO_RUN_001 |
| Versão | 1.16 |
| Data | 15/09/2026 |

Isto é **MVP demonstrável local** via Satellite Contract V1 (`SPIDER-SAT-003`, DEMO ONLY). Não é piloto comercial, homologação, produção nem proposta Icatu. Só se apresenta o que ocorreu e tem evidência. A fatia desta reunião (stack **nova** `:15178`): **(a)** URL pública real → revisão → intenção → possibilidades só do provider; **(b)** incêndios sintéticos → cotação simulada em R$. Exemplos governados continuam nomeados e separados. Não é cotação Icatu.

A jornada contextual do PRM_017 **não** está na stack da reunião (`:8095/:8080/:8088/:5178`) enquanto esses listeners forem os processos antigos sem ledger. A versão nova usa a **stack isolada** (`:19095/:19080/:19088/:15178` + Postgres `:15437` volume `segsense_pgdata_isolated_cor016`). O PRM_018 não muda essa topologia: a marca visível cresceu na URL nova; `:5178` continua código anterior. Não pare a reunião com `pids.txt` nem com `stop-mvp-demo.ps1` sem ledger da reunião.

## URL inicial

Reunião (código antigo, se ainda no ar): `http://127.0.0.1:5178/demonstracao/mvp-integrado`

**Versão nova (ativa para auditoria visual):** `http://127.0.0.1:15178/demonstracao/mvp-integrado`

Fontes governadas na stack isolada (não são artigos comerciais; não copie o texto integral):

- `http://127.0.0.1:15178/demonstracao/fontes/proximidade-incendios`
- `http://127.0.0.1:15178/demonstracao/fontes/continuidade-familiar`
- `http://127.0.0.1:15178/demonstracao/fontes/interrupcao-renda`
- `http://127.0.0.1:15178/demonstracao/fontes/revogada` (deve falhar)

Também a partir de `http://127.0.0.1:5178/` e, no bloqueio 401, `http://127.0.0.1:5178/admin/demonstracoes`.

Não usar `/go` nem `/spiderbank` como prova de seguros.

## Segredos locais (obrigatório, uma vez por máquina)

Os valores **não** estão no Git nem nesta página. Identidade pública (pode ser dita): `local-demo-segsense`. O segredo é outro material.

```powershell
Set-Location C:\Projetos\segsense\scripts
.\setup-mvp-demo-secrets.ps1
```

Isto grava `scripts/.mvp-secrets.env` (gitignored). Rotação: rode de novo e **reinicie** mock, Spider e BFF. Se o `start-mvp-demo.ps1` **desta** versão gravou `.mvp-logs/owned-run.json`, use `.\stop-mvp-demo.ps1` e depois o start. Se a stack foi só reutilizada (porta já ocupada) ou iniciada antes do COR_001, **não** há alvo verificável: inspecione PID/porta (`Get-NetTCPConnection`) e não mate por `pids.txt`. Não cole o arquivo de segredos em chat, log ou ata.

Se a porta já estiver ocupada por um processo antigo **sem** esses segredos, a jornada falha fechada (401). Pare o processo antigo antes da reunião.

## Como iniciar a versão nova (isolada; não destrói a reunião)

```powershell
Set-Location C:\Projetos\segsense\scripts
.\start-isolated-cor016.ps1
.\prove-isolated-prm017.ps1
```

O prove **não** encerra a stack. A URL `http://127.0.0.1:15178/demonstracao/mvp-integrado` permanece no ar para auditoria visual.

Portas: mock `:19095`, Spider `:19080`, BFF `:19088`, FE `:15178`, Postgres `:15437` (container `segsense-postgres-isolated-cor016`, volume **novo** `segsense_pgdata_isolated_cor016`). Não usa `docker compose` do volume `segsense_pgdata`. Porta isolada ocupada por processo estranho: `NÃO COMPROVADO`, sem kill. Parada só do ledger `.mvp-logs/owned-run-cor016.json`:

```powershell
.\stop-mvp-demo.ps1 -LedgerPath (Join-Path $PWD '.mvp-logs\owned-run-cor016.json')
```

`.\start-mvp-demo.ps1` continua sendo o start da reunião `:5178`. Se essa stack for anterior ao COR_001, **não** a use como prova da jornada nova.

## Como iniciar a reunião (não destrutivo; não é a prova COR_001)

```powershell
Set-Location C:\Projetos\segsense\scripts
.\start-mvp-demo.ps1
```

O script carrega os segredos **sem imprimir**, exige ACL restrita e termina com `preflight` de identidade dos três runtimes. Não derruba volumes Docker e não inicia Hub/Panne/School. Porta ocupada por processo estranho: erro legível, sem kill. Postgres `:5437` precisa já estar no ar se o compose não for usado. Só o listener que **este** start criou entra no ledger gitignored `.mvp-logs/owned-run.json`. Processo reutilizado **não** é alvo de parada. A migration V15 (fingerprint) aplica-se no BFF isolado; o volume da reunião `:5437` **não** é migrado por este corretivo.

```powershell
.\preflight-mvp-demo.ps1
```

## Parada (somente listeners comprovados desta partida)

O script antigo (PID de `pids.txt` + glob na command line) **não deve ser usado**. A parada automática nova só envia `Stop-Process` a um PID que seja o listener da porta gravada, com executável, marcador único `segsense.mvp.run=<guid>` e instante de início compatíveis com o ledger. Qualquer divergência: mensagem legível, processo intacto, ledger conservado para inspeção.

```powershell
.\stop-mvp-demo.ps1
```

Se não existir `.mvp-logs/owned-run.json` (stack da reunião reutilizada ou partida anterior ao COR_001), o script **recusa** e não mata nada. Nesse caso, inspecione manualmente as portas `:8095`, `:8080`, `:8088` e `:5178`. Wrappers Maven/`cmd` e filhos não verificados **não** são encerrados automaticamente.

Reset só da tabela demo (não apaga convites/admin):

```powershell
.\reset-mvp-demo.ps1
```

## Roteiro (cinco minutos)

1. Abrir a **URL nova** `:15178`. Watermark no topo. Primeira dobra: **1. Fonte ou relato**, **2. Elementos**, **3. Sua intenção** com campo **O que você quer fazer?** (texto livre; sem radios técnicos). Sem caixas “Confirmo esta intenção” / “não informei dados pessoais”. Detalhes técnicos recolhidos. Não usar `:5178` como jornada nova.
2. **Contexto A (incêndios).** Escrever “Houve incêndios nas proximidades” **ou** clicar em “incêndios próximos”. Dizer: o artigo é editorial sintético; **não** prova risco do imóvel da pessoa e **não** agrava preço.
3. Intenção: “Quero contratar um seguro residencial”. Mostrar “Entendi que você quer avaliar uma proteção residencial”. Frase: “Vamos calcular uma simulação; contratar de verdade depende de seguradora e produto autorizados.” Enviar **Gerar cotação simulada**. Aguardar só o texto de espera. Volta com **perguntas** (tipo de imóvel, valor, período) — ainda **sem R$**.
4. Responder: apartamento hipotético, R$ 300.000, 12 meses. Enviar de novo. Quando voltar: **Cotação simulada** com **R$ 540,00**, dados usados em reais, e “Como este valor foi calculado” em linguagem humana (capital, apartamento, 12 meses, prêmio). Sem `bps`, `APARTMENT` nem centavos na dobra pública. Watermark de simulação. **Não** é Icatu. Códigos só em `details`.
5. **URL pública (PRM_020_COR_001).** Colar artigo público (ex.: Wikipédia Agricultura no Brasil). **Obter conteúdo da URL**. O texto da fonte deve ser o artigo, não menu/login/sumário. Cartões só com relação local; cultura/região distantes **não** aparecem. Remover/corrigir antes de **Confirmar este contexto**. Intenção livre: “Quero entender opções de proteção para perda de produção”. **Ver possibilidades para este contexto**. Caminhos demonstrativos **sem R$** e perguntas de cultura/região/período/situação. Dizer: o texto não prova que a pessoa é produtora. **Não** deve aparecer cotação residencial nem exemplo governado no lugar da URL.
6. **Jornada antiga (íntegra).** Nova tentativa. Continuidade familiar + texto “entender opções ilustrativas”. Botão **Ver possibilidades ilustrativas**. Sem prêmio em R$.
7. Imprimir se preciso: só cenário e resultado da tentativa corrente. **Nova tentativa** limpa o resultado anterior. Pedido “quero pagar agora” é recusado na tela, sem chamar o simulador.

## Fallback honesto

Se a Spider ou o mock cair, a tela mostra indisponibilidade. **Não** improvise proposta. Não abra SpiderBank. Contexto insuficiente pede complemento (`MISSING_CONTEXT`). Conflito fonte/relato pede escolha (`AMBIGUOUS`).

## Conferência visual humana (lacuna se não houver browser interativo)

Não alegar aceite visual sem inspeção humana. Antes da reunião, uma pessoa deve conferir **sem gravar segredo**:

- [ ] 1440×900: watermark; Fonte / Elementos / **O que você quer fazer?**; sem radios técnicos; após perguntas e envio, **Cotação simulada** com R$ desta execução; IDs só em `details`; **logo SegSense reconhecível**
- [ ] 768×1024, 390×844, 320×568: texto, perguntas e botão alcançáveis; logo reconhecível sem overflow horizontal
- [ ] Zoom 200%: textarea e perguntas usáveis; marca ainda legível
- [ ] Tab: skip-link → logo «Voltar à apresentação» → nav → contexto → intenção → botão; anel roxo visível
- [ ] Ditado: se o navegador não suportar, estado claro e texto ainda utilizável. Copy: o SegSense não recebe/grava áudio. Ditado real com microfone: só com permissão explícita; se não exercido, marcar NÃO VERIFICADO
- [ ] Editar relato/URL/intenção depois de READY: resultado some; impressão não mistura entradas novas com valor antigo
- [ ] Link revogado e URL privada: erro, sem possibilidades nem prêmio
- [ ] Impressão: tentativa corrente + faixa de simulação; formulário/técnico recolhido; sem apólice
- [ ] URL pública: obter / revisar / confirmar são botões distintos; falha não troca por exemplo governado
- [ ] Quebra de safra: possibilidades do provider, sem R$ residencial
- [ ] Home `/` e `/demonstracao/icatu` intactas (posições do logo); admin 401 honesto; marca visível em todas

## Checklist técnico antes da reunião

- [ ] `.\setup-mvp-demo-secrets.ps1` já rodou nesta máquina (ACL restrita)
- [ ] `.\preflight-mvp-demo.ps1` ok (mock TEST DOUBLE, Spider Satellite V1, SegSense)
- [ ] `.\prove-mvp-http.ps1` (canônico legado + prova isolada de provedor indisponível; **não** mata `:8095`; não imprime segredos)
- [ ] `.\test-mvp-ops.ps1` (ACL + PID obsoleto no **script real** de parada; processo alheio permanece)
- [ ] V14 aplicada no Postgres demo (status novos); volumes **não** apagados
- [ ] Watermark visível
- [ ] Possibilidades só depois da resposta ilustrativa com `providerReference`; cotação simulada só depois de `premiumAnnualCents` + `quoteReference` desta execução; “pagar agora” sem chamar o mock

## O que pode / não pode ser dito

| Pode | Não pode |
|---|---|
| Demonstração local via Satellite Contract V1 (DEMO ONLY) | “Está integrado à Icatu” / “é produção” / “o mock é a seguradora” |
| “A Spider aplicou regras explícitas ao contexto e à intenção” | “A Spider compreendeu / interpretou a necessidade” / “Personalizamos um seguro” / “Provider Satellite certificado” |
| “Cotação simulada do mock demonstrativo; taxas inventadas; não é Icatu” | “Esta é a cotação / proposta / apólice Icatu” / “contratação efetivada” |
| “SegSense não conhece o provider; o provider não conhece a jornada” | “Sandbox Icatu” / “URL pública qualquer vira cotação” |
