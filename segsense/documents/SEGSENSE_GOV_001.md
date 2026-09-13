# SEGSENSE_GOV_001 — Governança editorial e autorização de publicação

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_GOV_001 |
| Título | Papéis, segregação, estados e significado de PUBLISHED |
| Categoria | GOV — governança |
| Versão | 1.2 |
| Status | Vigente nesta etapa |
| Data | 11/09/2026 |
| Dependências | SEGSENSE_DOM_002 v1.1; SEGSENSE_SEC_001 v1.3; SEGSENSE_PRM_006; SEGSENSE_PRM_006_COR_001 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Ciclo de vida editorial, segregação por sujeito e PUBLISHED como autorização interna. |
| 1.1 | 04/09/2026 | Submissão como fato imutável; decisão como fato distinto; abertura pelo ponteiro. |
| 1.2 | 11/09/2026 | Emissão/revogação de link usa `segsense.link.*`; sem quarto papel de SoD. |

## 1. Significado de PUBLISHED

`PUBLISHED` é **autorização ativa para publicação dentro do SegSense**. Não envia dados à Spider nem integra Icatu. O link contextual seguro é um aggregate distinto (`SEGSENSE_LNK_001`): só pode ser emitido quando `effectivelyPublished=true`. A página pública do usuário permanece no PRM_008.

`effectivelyPublished` é leitura derivada: status `PUBLISHED` **e** hierarquia efetivamente disponível **e** janela UTC aberta. Suspensão de Publisher, Channel ou Environment não altera o status persistido.

## 2. Papéis e segregação

Identidade vem apenas do `Authentication` confiável (`CatalogActor.subjectId`). Nunca de payload ou header ad hoc.

| Papel técnico | Authority necessária | Sujeito |
|---|---|---|
| Autor / editor | `segsense.opportunity.write` | cria revisão |
| Submissor | `segsense.opportunity.submit` | submete a revisão corrente |
| Revisor | `segsense.opportunity.review` | devolve, aprova ou rejeita |
| Gestor de publicação | `segsense.publication.manage` | ativa, pausa, retoma, expira, revoga |
| Consulta | `segsense.opportunity.read` | detalhe, governança e eventos |
| Emissor de link | `segsense.link.manage` | emite e revoga links contextuais |
| Consulta de link | `segsense.link.read` | lista, detalhe e eventos do link |

Regras de sujeito (não substituídas pela authority):

- quem criou a revisão corrente ou submeteu não pode aprovar, rejeitar nem devolver;
- quem aprovou não pode ativar a publicação da mesma revisão.
- emitir ou revogar link **não** exige sujeito distinto do autor/aprovador/ativador: GOV_001 não define um quarto papel de SoD para o link.

Ausência de IdP continua produzindo 401 no runtime. Não há usuário, login, token ou autenticação simulada.

## 3. Máquina de estados

```text
DRAFT
  -> UNDER_REVIEW        submit

UNDER_REVIEW
  -> DRAFT               return-for-changes
  -> APPROVED            approve
  -> REVOKED             reject

APPROVED
  -> PUBLISHED           activate-publication
  -> REVOKED             revoke

PUBLISHED
  -> PAUSED              pause
  -> REVOKED             revoke
  -> EXPIRED             expire

PAUSED
  -> PUBLISHED           resume
  -> REVOKED             revoke
  -> EXPIRED             expire
```

## 4. Invariantes

- Toda decisão aplica-se a uma revisão exata e imutável.
- Nenhuma revisão é aprovada por criação, edição, data ou chamada técnica.
- `DRAFT` é o único estado em que uma nova revisão pode ser criada.
- `submit` insere uma única vez um fato imutável de submissão e fixa `submittedRevision` à revisão corrente.
- A submissão atualmente aberta é a apontada por `openSubmissionId` **e** ainda sem `opportunity_decision`.
- O encerramento da submissão é outro fato: a inserção de exatamente uma `opportunity_decision`, com limpeza atômica do ponteiro no aggregate. A linha da submissão não é atualizada.
- A coluna persistida `opportunity_submission.status` é histórica e deprecada; novas linhas podem nascer `OPEN`, mas esse valor não significa “aberta agora”.
- Há no máximo um ponteiro de submissão aberta por oportunidade.
- Há no máximo uma decisão por submissão.
- `approve` vincula exatamente `approvedRevision`; ela não migra para revisão posterior.
- `activate-publication` exige APPROVED, revisão aprovada ainda corrente, hierarquia efetivamente disponível e janela UTC aberta.
- `validFrom` no futuro ou `validUntil` já atingido impede ativar e retomar (`PUBLICATION_WINDOW_NOT_OPEN`).
- `expire` só é permitido quando `validUntil <= now` (`PUBLICATION_NOT_EXPIRED` caso contrário).
- `revoke` e `reject` exigem justificativa administrativa (10–500, sem HTML/script) e são terminais.
- Idempotência por estado não mascara transição inválida.
- Não há exclusão nem retorno de estados terminais.
- Não há scheduler de ativação.
- Eventos, submissões e decisões são append-only, correlacionados, sem token, credencial, payload integral ou dado pessoal.
- `availableActions` é conveniência de apresentação; o comando revalida authority, sujeito, versão, revisão e estado.

## 5. Fora desta governança

Estas regras são editoriais e técnicas. Não representam análise atuarial, recomendação, elegibilidade, produto, preço, cobertura ou decisão securitária. Nenhum estado local decide capability, route, adapter ou plano da Spider.
