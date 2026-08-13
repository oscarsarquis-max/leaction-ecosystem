# Roteiro de Homologação — inove4us School + Inove (produção)

## Registro da sessão

| Campo | Valor |
|---|---|
| Data | ______ |
| Versão/SHA testado | School: ______ · Inove: ______ — conferir em `/api/health` (esperado no deploy atual: School `0.2.0` / Inove `2.2.0`, SHA `5c47834` se ainda for o último deploy) |
| Participantes | Você (técnico) · Pedagoga (persona Escola) · Professora (persona Professor) |
| Prefixo dos dados de demo desta sessão | `HOMOLOG-AAAAMMDD-` (use em nome de unidade, curso, turma, aluno — facilita limpeza depois) |
| Conta gestor da pedagoga | ☐ sysadmin (3 zonas) · ☐ gestor com escopo limitado (e-mail: ______ · zonas: ______) |
| Resultado geral | ☐ Passou · ☐ Travou em algum ponto · ☐ Não concluído |

Fluxo natural do smoke em duas personas (Escola → Professor → Ponte). Use como roteiro da visita; marque o que passou / travou / "não entendi". Tempo alvo: **60–90 min** (A 25 · B 30 · C 15 · feedback 10).

URLs: Escola `https://school.inove4us.com.br` · Professor `https://inove4us.com.br`

---

## Antes (você prepara — 15–20 min)

Sistemas ainda podem estar em "em breve": use **bypass** nos dois hosts (cookie de sessão de homologação) e tenha contas prontas. Preferir **janela anônima** por host para não misturar sessões.

| Item | OK? |
|---|---|
| Bypass School + login gestor | ☐ |
| Conta professor no Inove (e-mail real dela) — anotar se a conta **já existe** ou será criada na hora | ☐ |
| Catálogo de metodologias: abrir no Editor e confirmar que a lista carrega (em prod já há **39** ativas seedadas; se a UI falhar, avisar a pedagoga) | ☐ |
| Se for usar `/market` no opcional D: confirmar gate por zona **administrativo** (não senha mockup) | ☐ |
| Em School já existe (ou você cria agora com prefixo `HOMOLOG-`): 1 unidade, 1 período, 1 curso, 1 disciplina, 1 turma, 2–3 alunos | ☐ |
| Convite da professora ainda não aceito (ou reenviar na hora) | ☐ |
| Se o check de RBAC (passo A1) for obrigatório: criar gestor **com zonas limitadas** para a pedagoga — o sysadmin `admin@i4uschool.com.br` tem as 3 zonas e mostra o menu completo | ☐ |
| Avisar: isto é **homologação**, dados de demo (prefixo `HOMOLOG-`); instituição atual em prod costuma ser a seed Horizonte | ☐ |

---

## A) Escola — Torre de Controle (persona: coordenação / pedagoga)

Ordem natural = o que a secretaria monta **antes** da aula existir.

**1. Entrada**
- [ ] Login em `/acesso`
- [ ] Vê o menu permitido pelas zonas dela (Radar · Editor · Secretaria · Equipe — conforme RBAC)
- [ ] **Se a conta for de escopo limitado:** confirma que **não** aparece o menu completo de administrador. Se a conta for sysadmin, anote "N/A — 3 zonas" e siga. Se travar: relogar; se persistir com conta limitada, checar `school_gestor_perfis` com o técnico

**2. Secretaria Acadêmica (`/secretaria`) — estrutura**
- [ ] Confere/abre a Unidade (ficha: endereço/equipe se quiser)
- [ ] Confere período letivo ativo
- [ ] Vê curso → disciplina → turma (drill-down — um clique no curso revela turmas e disciplinas)
- [ ] Vê alunos na turma
- [ ] (Opcional) Importa CSV: baixa o modelo, importa na turma filtrada; reimportar a **mesma matrícula** atualiza em vez de duplicar
- [ ] Entende a aba Situação por período (nota o aviso: é foto do agora, não histórico longo)

**3. Minha Equipe (`/equipe`) — convite**
- [ ] Convida a professora (e-mail dela)
- [ ] Dispara convite e **copia o `invite_url`** da UI/API — **não espere e-mail**: o fluxo atual faz push `TEACHER_INVITE` para o Inove e devolve o link; não há SMTP neste passo
- [ ] Técnico anota o resultado do push (`b2c_push.ok` / `pending` / erro) — integração é fail-soft
- [ ] Status fica **pendente** até ela aceitar **ou** pode virar **ativo** logo se já existir conta Inove com o mesmo e-mail (bind automático) — anotar qual caso ocorreu

**4. Secretaria — alocação**
- [ ] Aloca a professora na turma + disciplina
- [ ] (Opcional) Publica um aviso / planejamento simples para a mesa — no bloco C confirma que apareceu para essa professora/turma
- [ ] Isolamento multi-escola ("não vaza para outra escola"): ☐ N/A nesta sessão (só há uma instituição em prod) · ☐ testado com 2ª instituição criada para o teste

**5. Editor Pedagógico (`/editor-pedagogico`)**
- [ ] Abre o catálogo / uma metodologia e confere que há conteúdo (passos)
- [ ] Entende o pilar de inclusão / PEI (mesmo sem fechar um PEI completo)
- [ ] Nota: "aqui a escola governa o método"
- [ ] (Opcional forte — só se sobrar tempo no A) ativar adaptação/PEI de **um aluno nomeado** da turma `HOMOLOG-` para testar o card no bloco B

**6. Radar Pedagógico (`/`) — ainda pode estar vazio**
- [ ] Entende o Grafo / listas / agenda
- [ ] Combina: "depois que ela der aula, voltamos aqui"

**Checkpoint A** — "Ficou claro o que a escola faz *antes* do professor abrir a aula?"

---

## B) Professor — Trincheira / Mesa (persona: professora)

**7. Aceite do convite (Inove)**
- [ ] Abre o **`invite_url`** copiado (formato típico: `/acesso?email=...&school_invite=1`)
- [ ] Login/cadastro no Inove
- [ ] Aceita / confirma vínculo com a escola (se ainda pendente)
- [ ] Cai na Mesa do Inovador (`/mesa-do-inovador`)

**8. Mesa — preparo**
- [ ] Vê card/aula da turma alocada (ou cria/recebe o planejamento)
- [ ] Abre o roteiro da aula (Markdown / passos da metodologia)
- [ ] (Se houver) vê aviso pinado no card
- [ ] (Opcional forte — só se PEI individual foi ativado no A) confirma que o **nome do aluno** bate no card dela. A integração é fail-soft: falha silenciosa é esperada por design — o check serve para distinguir "não apareceu porque é normal" de "não apareceu porque quebrou"

**9. Execução da aula (fluxo curto)**
- [ ] Entra no desafio / execução
- [ ] Move cards no Kanban da mesa (gera rastro do diário)
- [ ] Fecha a aula com Diário de bordo
- [ ] (Opcional forte) envia sugestão de curadoria no fechamento

**Checkpoint B** — "Isto alivia burocracia ou ainda parece formulário?"

---

## C) Ponte — o que a escola enxerga depois

Volta no School com a pedagoga (mesma sessão ou outra aba).

**10. Radar de novo**
- [ ] Aparece a aula / plano espelhado
- [ ] Abre o mesmo card que a professora viu (espelho)
- [ ] Se ela enviou sugestão: aparece na curadoria / fila lilás / atalho do Editor
- [ ] Se um aviso foi publicado no passo 4: confirma que apareceu para a turma/unidade certa

**11. Equipe — radiografia do professor**
- [ ] Abre a professora na Equipe
- [ ] Vê linha do tempo: convite → aceite → entrega

**Checkpoint C** — "A escola vê a verdade da ponta sem 'traduzir' o que o professor fez?"

---

## D) Opcional (só se sobrar tempo)

| Item | Para quê | OK? |
|---|---|---|
| `/market` (só gestor com zona administrativo; gate real) | discurso produto — não é operação | ☐ |
| Import CSV alunos (se não fez no A2) | secretaria em escala | ☐ |
| 2ª metodologia no Editor | repertório | ☐ |

**Não priorize no 1º dia:** Action Hub, cobrança, unlock público, limpeza Horizonte, criação de 2ª instituição só para isolamento (deixar para sessão dedicada).

---

## Fechamento da sessão (não pule)

Bypass **não tem** endpoint de "revogar". É cookie de sessão (`is_admin_tester`). Lock/unlock controla o público.

- [ ] Fechar as abas de homologação / limpar cookies (ou encerrar as janelas anônimas) nos dois hosts
- [ ] Confirmar que **não** foi chamado `/gatekeeper/unlock` por engano
- [ ] Confirmar `/gatekeeper/status` (ou página pública) → os 3 domínios continuam **trancados** para o público (`locked: true`)
- [ ] Confirmar que todo dado criado na sessão está com o prefixo `HOMOLOG-` (para o próximo script de limpeza)
- [ ] (Técnico) Anotar gaps fail-soft observados (convite, aviso, PEI, espelho) para backlog

---

## Folha de feedback (5 minutos no fim)

Para cada bloco (Secretaria / Equipe / Editor / Mesa / Radar), ela marca:

1. Entendi o propósito? (sim / mais ou menos / não)
2. Travou em algum clique? (qual)
3. Linguagem estranha? (palavra)
4. Falta o quê para usar numa escola real amanhã?
5. Severidade do que travou: bloqueia lançamento / incomoda / cosmético

---

## Papéis na sessão

| Quem | Faz |
|---|---|
| Você (técnico) | bypass, contas, copiar `invite_url`, registro paralelo (`b2c_push`, `notificado_b2c`, logs), "socorro" se travar |
| Pedagoga | persona Escola (A + C) — opinião de coordenação |
| Mesma pessoa ou outra | persona Professora (B) — opinião de sala |
| Tempo alvo | 60–90 min (A 25 · B 30 · C 15 · feedback 10) |

---

## Notas técnicas (para o piloto)

1. **Grafo acadêmico vazio:** sem o bloco "Antes" (turma + convite + alocação), o percurso B/C não anda.
2. **Fail-soft School→B2C:** falha de integração não trava o professor e muitas vezes **não avisa** na UI — por isso os checks "confirma que apareceu" são essenciais, não opcionais.
3. **Convite:** entrega o link na School; não envia e-mail transacional neste fluxo.
4. **RBAC:** menu = união das zonas em `school_gestor_perfis`. Sysadmin ≠ teste de escopo.
5. **Limpeza:** não apagar a instituição Horizonte inteira sem decisão explícita — limpar só registros `HOMOLOG-*` da sessão.
