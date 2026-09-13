# SEGSENSE_DEMO_RUN_001 — Roteiro de 5 minutos (reunião local)

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_DEMO_RUN_001 |
| Versão | 1.3 |
| Data | 13/09/2026 |

Isto é **MVP demonstrável local** via Satellite Contract V1 (`SPIDER-SAT-003`, DEMO ONLY). Não é piloto comercial, homologação, produção nem proposta Icatu. Só se apresenta o que ocorreu e tem evidência.

## URL inicial

`http://127.0.0.1:5178/demonstracao/mvp-integrado`

Também a partir de `http://127.0.0.1:5178/` e, no bloqueio 401, `http://127.0.0.1:5178/admin/demonstracoes`.

Não usar `/go` nem `/spiderbank` como prova de seguros.

## Segredos locais (obrigatório, uma vez por máquina)

Os valores **não** estão no Git nem nesta página. Identidade pública (pode ser dita): `local-demo-segsense`. O segredo é outro material.

```powershell
Set-Location C:\Projetos\segsense\scripts
.\setup-mvp-demo-secrets.ps1
```

Isto grava `scripts/.mvp-secrets.env` (gitignored). Rotação: rode de novo e **reinicie** mock, Spider e BFF (`.\stop-mvp-demo.ps1` e depois `start`). Não cole o arquivo em chat, log ou ata.

Se a porta já estiver ocupada por um processo antigo **sem** esses segredos, a jornada falha fechada (401). Pare o processo antigo antes da reunião.

## Como iniciar (não destrutivo)

```powershell
Set-Location C:\Projetos\segsense\scripts
.\start-mvp-demo.ps1
```

O script carrega os segredos **sem imprimir**, exige ACL restrita e termina com `preflight` de identidade dos três runtimes. Não derruba volumes Docker e não inicia Hub/Panne/School. Porta ocupada por processo estranho: erro legível, sem kill. Postgres `:5437` precisa já estar no ar se o compose não for usado.

```powershell
.\preflight-mvp-demo.ps1
```

Parar só o que o script iniciou:

```powershell
.\stop-mvp-demo.ps1
```

Reset só da tabela demo (não apaga convites/admin):

```powershell
.\reset-mvp-demo.ps1
```

## Roteiro (cinco minutos)

1. Abrir a URL. O watermark está no topo. A promessa sintética e o botão **Enviar à Spider** devem aparecer sem rolagem longa em 1440×900.
2. Dizer: artigo fictício (bloco recolhido); o SegSense (EXPERIENCE) obtém o contexto de um registro governado no servidor, não da URL; a Spider decide via Satellite Contract V1; o mock só ilustra uma capability. **TEST DOUBLE / NOT ICATU**. Detalhes técnicos (satelliteId, contrato v1, correlation) ficam recolhidos.
3. Marcar a confirmação. Objetivo único da reunião: entender opções ilustrativas. Enviar.
4. Aguardar **somente** “Aguardando resposta da Spider…” (fato do cliente). Não há fase “em análise”. Quando a resposta canônica confirmar `decisionId` e referência de provedor, mostrar pré-proposta: contexto ecoado, itens ilustrativos e pendências. IDs ficam em “IDs de correlação e prova técnica”.
5. Se alguém perguntar cotação vinculante: isso **não** está na escolha da reunião; a recusa existe só como teste técnico (`REQUEST_BINDING_QUOTE` via `prove-mvp-http.ps1`).
6. Imprimir pelo navegador se preciso. O watermark permanece. Não gerar PDF oficial.

## Fallback honesto

Se a Spider ou o mock cair, a tela mostra indisponibilidade. **Não** improvise proposta. Não abra SpiderBank.

## Conferência visual humana (lacuna desta sessão)

Não houve browser interativo nesta execução. Não alegar aceite visual. Antes da reunião, uma pessoa deve conferir **sem gravar segredo**:

- [ ] 1440×900: disclaimer, promessa e **Enviar à Spider** acima da dobra
- [ ] 768×1024, 390×844, 320×568: texto legível, botão alcançável
- [ ] Zoom 200%: formulário usável
- [ ] Tab: skip-link → confirmação → botão
- [ ] Watermark no topo e na pré-proposta (tela e impressão)
- [ ] Nenhum logo Icatu, R$ ou “cotação vinculante” na escolha principal
- [ ] Home `/` e `/demonstracao/icatu` intactas; admin 401

## Checklist técnico antes da reunião

- [ ] `.\setup-mvp-demo-secrets.ps1` já rodou nesta máquina (ACL restrita)
- [ ] `.\preflight-mvp-demo.ps1` ok (mock TEST DOUBLE, Spider Satellite V1, SegSense)
- [ ] `.\prove-mvp-http.ps1` (endpoint canônico; não imprime segredos)
- [ ] Watermark visível
- [ ] `providerReference` só depois da resposta; `origin=ILLUSTRATIVE_NOT_ICATU_CONTRACT`

## O que pode / não pode ser dito

| Pode | Não pode |
|---|---|
| Demonstração local via Satellite Contract V1 (DEMO ONLY) | “Está integrado à Icatu” / “é produção” / “o mock é a seguradora” |
| “A Spider decidiu; o mock só executou a capability ilustrativa” | “Personalizamos um seguro” / “Provider Satellite certificado” |
| “Itens ilustrativos, não ofertáveis” | “Esta é a cotação / proposta / apólice” |
| “SegSense não conhece o provider; o provider não conhece a jornada” | “Sandbox Icatu” |
