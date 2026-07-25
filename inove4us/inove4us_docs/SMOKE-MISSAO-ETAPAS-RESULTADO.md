# Smoke Missao Etapas 1-4 - Resultado

Data: 2026-07-25 10:28:10
Professor: inovador@inove4us.com.br (id_clie=16)

| Item | Status | Evidencia | Causa raiz |
|------|--------|-----------|------------|
| E0-login | PASSOU | id_clie=16 creditos=3 |  |
| A1-instituicao | PASSOU | id=1 nome=Escola Exemplo |  |
| A1-periodo1 | PASSOU | id=1 em_curso=True |  |
| A2-periodo2 | PASSOU | id=2 |  |
| A2-unico-em-curso | PASSOU | count=1 map=1:false,2:true |  |
| A1-curso | PASSOU | id=1 |  |
| A1-disciplina | PASSOU | id=1 nome=Matematica |  |
| A3-bloqueio-curso | PASSOU | HTTP 409 code= |  |
| B1-aula-sem-vinculo | PASSOU | id=1 origem=manual evento=13 |  |
| B2-aula-com-vinculo | PASSOU | id=2 db=1/manual agenda=14 (origem manual = Dia a Dia) |  |
| B3-grafo | PASSOU | edge 15->16; nodes=7 edges=1 |  |
| C1-contadores | PASSOU | lote=1 sucesso=3 erro=1 aviso=0 |  |
| C1-lote-db | PASSOU | inove_importacoes_lote id=1 |  |
| C1-relatorio-erro | PASSOU | AULA-BAD: data inválida ou ausente (use ISO YYYY-MM-DD) |  |
| C2-agenda | PASSOU | 3 eventos em inove_agenda_eventos |  |
| C2-aulas-simples | PASSOU | 2 aulas draft com id_evento_agenda ok; EVT-001 sem Dia a Dia |  |
| C3-vinculo-pai | PASSOU | AULA-002.id_evento_pai -> AULA-001; edge no grafo |  |
| C4-idempotencia | PASSOU | criados=0 atualizados=3 agenda_unica=3 lote2=2 |  |
| C5-freemium | PASSOU | sucesso=2 erro=0 aviso=0 |  |
| C6-aviso-miss | PASSOU | aviso=1 disciplina_id=null msg=criado; disciplina 'DisciplinaQueNaoExisteXYZ20260725102757' não encontrada no cadastro — registro sem vínculo |  |
| C7-badge-filtro | PASSOU | filtro n=3; AULA-001 ok; badge FE presente |  |
| D1-import-401 | PASSOU | POST sem sessao -> 401 |  |
| D2-lote-alheio | PASSOU | GET lote 5  INSERT 0 1 (clie 12) -> 404 |  |
| D3-ownership-404 | PASSOU | periodo/curso/disciplina alheios -> 404/404/404 |  |
| E1-auth-me | PASSOU | creditos=3 notices=0 |  |
| E2-wizard-credito | PASSOU | estruturar OK; creditos 3 -> 2 |  |
| E3-mesa-importar | PASSOU | FE /mesa-do-inovador HTTP 200; Link Importar no source |  |

**Totais:** PASSOU=27 Â· FALHOU=0 Â· PULADO=0
