# Wizard/Desafio — hipóteses sem vazamento (anti-desc_prob)

## 0. Diagnóstico (causa exata — 1ª rodada)

**Cenário dominante: (b) fallback determinístico / pós-processamento com texto da base.**

Em `_fallback_payload` legado, a UI montava causas com `desc_prob` / `razoes_prob`
de `ctdi_problemas_referencia` (Absenteísmo / smartphones).

## 0.1 Recorrência “Escola Recanto” (3ª rodada — causa específica)

**Não** era um segundo caminho A/B/C esquecido, nem cache de resposta.

Causa documentada:

1. O card **“Seu contexto”** é montado por `causas_somente_do_relato`, que
   **ecoava o campo HTTP `contexto`** da requisição dentro de
   `No contexto «{contexto}»…`.
2. No reteste do córrego, o relato em `problema` estava correto (Vale Verde),
   mas o campo **Localização / contexto** do formulário ainda trazia o valor
   de um teste anterior (`Escola Recanto, 8º ano do Fundamental II, turno Manhã.`).
3. Quando a IA devolvia só 2 causas boas, o **pad do 3º/2º slot** reimprimia
   esse `contexto` stale — parecendo vazamento da base, embora viesse do form.

Mitigações:
- `contexto_seguro_para_ui`: só ecoa `contexto` se ancorado no relato atual e
  limpo da barreira; senão usa entidades do próprio relato (ex. Escola Municipal Vale Verde).
- Barreira final contra a **tabela inteira** de `ctdi_problemas_referencia`.

## 0.2 Eco de formulário / tokens soltos

Templates antigos do pad listavam tokens isolados (`ciências, municipal e vale`)
e ecoavam `Título sugerido:` / `Elementos concretos a preservar`. Corrigido com
`expressoes_do_relato` + templates em frases naturais.

## 0.3 Pad achatando IA boa (4ª rodada)

**Confirmado:** o pós-processamento (`sanitizar` com âncora rígida +
`forcar_ancoragem` / `_completar_causas_com_pad`) reescrevia causas da IA
mesmo quando já passavam em vazamento — bastava não citar os mesmos 1–2
substantivos próprios. Resultado: 3 frases repetindo “córrego do Sabiá /
Escola Municipal Vale Verde”.

**Correção:** `causa_passa_checagens` + `vinculo_minimo_com_relato` (mais
permissivo); pad **só** no slot que falhou; 3 causas IA boas → intactas até a
tela. Prompt reforça ângulos distintos na mesma chamada.

| Item | Ação |
|------|------|
| Barreira final | `aplicar_barreira_final_payload` vs corpus completo (DB) |
| Contexto | `contexto_seguro_para_ui` — nunca Recanto stale |
| Expressões | `expressoes_do_relato` (córrego do Sabiá, escola, concurso, turmas) |
| Pad | Frases naturais; 3º slot pode marcar `precisa_complemento` |
| Complementação | Campo FE condicional; soma ao relato; reestruturar completo |
| Gate | `precisa_retry` ≤ 1 por chamada estruturar |

**Custo:** ~1 chamada/desafio no comum; +1 retry se checagem falhar.
**Complementação:** nova chamada `estruturar` (1 crédito), com o mesmo orçamento
interno de 1+1 retry nessa chamada — não é “grátis” nem reaproveita a chamada
já consumida do primeiro estruturar (documentado: custo adicional = 1 crédito
por complemento).

## 2. Decisão de produto (3º slot / complemento)

- Retry compartilhado cobre `< 3` causas IA.
- Se ainda faltar qualidade, pad legível com expressões do relato.
- Slot `precisa_complemento=true` mostra caixa opcional na etapa 2; ao enviar,
  o relato é ampliado e a análise é **refeita** (não concatena texto velho).

## 3. Critério de pronto

- [x] Barreira final com teste de injeção proposital de texto da base
- [x] Causa da recorrência Recanto documentada (seção 0.1)
- [x] Expressões coerentes no pad (sem tokens soltos)
- [x] Campo de complementação condicional (FE + BE)
- [x] Suíte `test_wizard_antivazamento.py` cobre barreira + Recanto + tokens
- [ ] Teste manual no UI com relato do Sabiá + contexto stale limpo
