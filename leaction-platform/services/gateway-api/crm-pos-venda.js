'use strict';

/**
 * Sponge — pós-venda / onboarding por conta (prompt 141).
 * Limiares e severidades: editar só este objeto. Sem tabela nova, sem job.
 */

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/** Ajustável sem mudar o restante do código. */
const LIMIARES = {
  pagou_nao_logou: { dias: 2, severidade: 'alta' },
  logou_nao_montou: { dias: 3, severidade: 'alta' },
  convites_sem_aceite: { dias: 3, severidade: 'media' },
  aceitou_nao_usou: { dias: 3, severidade: 'media' },
  parou_de_usar: { dias: 5, severidade: 'alta' },
  licenca_ociosa: { dias: 14, razao: 0.2, severidade: 'media' },
};

const PESO_SEVERIDADE = { alta: 2, media: 1 };

const ETAPAS = [
  { n: 1, chave: 'contratou', rotulo: 'Contratou' },
  { n: 2, chave: 'gestor_login', rotulo: 'Gestor fez o primeiro login' },
  { n: 3, chave: 'senha_alterar', rotulo: 'Gestor alterou a senha temporária' },
  { n: 4, chave: 'criou_turmas', rotulo: 'Criou turmas' },
  { n: 5, chave: 'cadastrou_alunos', rotulo: 'Cadastrou alunos' },
  { n: 6, chave: 'convidou_professores', rotulo: 'Convidou professores' },
  { n: 7, chave: 'professores_aceitaram', rotulo: 'Professores aceitaram' },
  { n: 8, chave: 'professores_usaram', rotulo: 'Professores usaram' },
  { n: 9, chave: 'uso_recorrente', rotulo: 'Uso recorrente' },
];

const USO_PROFESSOR = [
  'aula_criar',
  'desafio_criar',
  'wizard_gerar',
  'pei_aplicar',
  'credito_consumir',
];

function iso(value) {
  if (value == null || value === '') return null;
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

function asInt(value) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : 0;
}

function ymdSp(value) {
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' });
}

function daysSinceSp(when, now = new Date()) {
  const a = ymdSp(when);
  const b = ymdSp(now);
  if (!a || !b) return null;
  return Math.round((Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / 86400000);
}

function parseIsoParam(raw, label) {
  const s = String(raw || '').trim();
  if (!s) return { value: null };
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) {
    return { error: `${label} deve ser ISO válido` };
  }
  return { value: d };
}

function etapaShape(feito, quando, fonte, now, quantidade = null, quantidadeRotulo = null) {
  const ts = iso(quando);
  return {
    feito: Boolean(feito),
    quando: ts,
    dias_desde: feito && ts ? daysSinceSp(ts, now) : null,
    fonte: fonte || null,
    quantidade: quantidade == null ? null : asInt(quantidade),
    quantidade_rotulo: quantidadeRotulo == null ? null : String(quantidadeRotulo),
  };
}

function nomeFromMeta(meta) {
  const m = meta && typeof meta === 'object' ? meta : {};
  const hub = m.hub_payload && typeof m.hub_payload === 'object' ? m.hub_payload : {};
  for (const c of [hub.razao_social, m.razao_social]) {
    const t = String(c || '').trim();
    if (t) return t.slice(0, 240);
  }
  return null;
}

function snapObj(dados) {
  return dados && typeof dados === 'object' ? dados : {};
}

function conviteIdOf(dados) {
  if (!dados || typeof dados !== 'object') return null;
  const raw = dados.convite_id || dados.professor_id;
  if (raw === null || raw === undefined || raw === '') return null;
  return String(raw);
}

function montarEtapas(row, now = new Date()) {
  const temSnap = row.snap_school != null && typeof row.snap_school === 'object';
  const snap = snapObj(row.snap_school);
  const vinculo = snap.professores_vinculo && typeof snap.professores_vinculo === 'object'
    ? snap.professores_vinculo
    : {};
  const lic = snap.licencas && typeof snap.licencas === 'object' ? snap.licencas : {};
  const turmasSnap = asInt(snap.turmas);
  const alunosSnap = asInt(snap.alunos);
  const convSnap = asInt(vinculo.pendente) + asInt(vinculo.ativo);
  const aceitosSnap = asInt(vinculo.ativo);
  const nConvEvento = asInt(row.n_convidar);
  const nAceiteEv = asInt(row.n_aceitar);
  const nUsando = asInt(row.n_prof_usando);
  const diasUso7d = asInt(row.dias_uso_7d);
  const convidados = Math.max(nConvEvento, convSnap);
  const aceitos = Math.max(nAceiteEv, aceitosSnap);
  const emUso = lic.em_uso != null ? asInt(lic.em_uso) : aceitos;
  const totalLic = lic.total_assentos != null ? asInt(lic.total_assentos) : asInt(row.seats);
  const rotuloSemSnap = 'sem snapshot ainda';

  const contratouEm = row.contratou_em;
  const e1 = etapaShape(Boolean(contratouEm), contratouEm, contratouEm ? 'contracts' : null, now);

  const loginEm = row.login_gestor;
  const e2 = etapaShape(Boolean(loginEm), loginEm, loginEm ? 'login_sucesso' : null, now);

  const senhaEm = row.senha_alterar;
  const e3 = etapaShape(Boolean(senhaEm), senhaEm, senhaEm ? 'senha_alterar' : null, now);

  const turmaEv = row.turma_criar;
  const e4feito = Boolean(turmaEv) || turmasSnap > 0;
  const e4 = etapaShape(
    e4feito,
    turmaEv || null,
    turmaEv ? 'turma_criar' : turmasSnap > 0 ? 'conta_snapshot' : null,
    now,
    temSnap ? turmasSnap : null,
    temSnap ? `${turmasSnap} turmas` : rotuloSemSnap
  );

  const alunoEv = row.aluno_matricular;
  const e5feito = Boolean(alunoEv) || alunosSnap > 0;
  const e5 = etapaShape(
    e5feito,
    alunoEv || null,
    alunoEv ? 'aluno_matricular' : alunosSnap > 0 ? 'conta_snapshot' : null,
    now,
    temSnap ? alunosSnap : null,
    temSnap ? `${alunosSnap} alunos` : rotuloSemSnap
  );

  const e6feito = nConvEvento > 0 || convSnap > 0;
  const e6quando = row.primeiro_convidar || null;
  const e6 = etapaShape(
    e6feito,
    e6quando,
    nConvEvento > 0 ? 'professor_convidar' : convSnap > 0 ? 'conta_snapshot' : null,
    now,
    convidados,
    `${convidados} convidados`
  );

  const e7feito = nAceiteEv > 0 || aceitosSnap > 0;
  const e7 = etapaShape(
    e7feito,
    row.primeiro_aceite || null,
    nAceiteEv > 0 ? 'convite_escola_aceitar' : aceitosSnap > 0 ? 'conta_snapshot' : null,
    now,
    aceitos,
    `${aceitos} de ${convidados} aceitaram · licenças ${emUso}/${totalLic}`
  );

  const e8 = etapaShape(
    nUsando > 0,
    row.primeiro_uso_prof || null,
    nUsando > 0 ? 'uso_professor' : null,
    now,
    nUsando,
    `${nUsando} de ${convidados} usando`
  );

  const e9feito = diasUso7d >= 2;
  const e9 = etapaShape(
    e9feito,
    e9feito ? row.ultimo_uso_prof : null,
    e9feito ? 'uso_recorrente' : null,
    now,
    diasUso7d,
    `${diasUso7d} dias ativos em 7`
  );

  const etapas = {
    contratou: e1,
    gestor_login: e2,
    senha_alterar: e3,
    criou_turmas: e4,
    cadastrou_alunos: e5,
    convidou_professores: e6,
    professores_aceitaram: e7,
    professores_usaram: e8,
    uso_recorrente: e9,
  };

  let etapaAtual = 0;
  for (const def of ETAPAS) {
    if (etapas[def.chave] && etapas[def.chave].feito) etapaAtual = def.n;
  }

  return {
    etapas,
    etapa_atual: etapaAtual,
    professores: {
      convidados,
      aceitos,
      usando: nUsando,
    },
    licencas: {
      em_uso: emUso,
      total: totalLic,
    },
    snap,
    turmasSnap,
    alunosSnap,
  };
}

function avaliarAlertas(
  {
    etapas,
    professoresDetalhe = [],
    professoresCounts,
    licencas,
    ultimoUsoProf,
    teveUsoProf,
  },
  now = new Date(),
  limiares = LIMIARES
) {
  const alertas = [];
  const e = etapas;
  const cfg = limiares;

  if (e.contratou.feito && !e.gestor_login.feito) {
    const dias = e.contratou.dias_desde;
    if (dias != null && dias >= cfg.pagou_nao_logou.dias) {
      alertas.push({
        chave: 'pagou_nao_logou',
        severidade: cfg.pagou_nao_logou.severidade,
        explicacao: `Contrato há ${dias} dia(s) sem o primeiro login do gestor no School.`,
      });
    }
  }

  if (e.gestor_login.feito) {
    const montou = e.criou_turmas.feito || e.cadastrou_alunos.feito || e.convidou_professores.feito;
    const dias = e.gestor_login.dias_desde;
    if (!montou && dias != null && dias >= cfg.logou_nao_montou.dias) {
      alertas.push({
        chave: 'logou_nao_montou',
        severidade: cfg.logou_nao_montou.severidade,
        explicacao: `Gestor logou há ${dias} dia(s) e ainda não criou turmas, alunos ou convites.`,
      });
    }
  }

  const pendentes = professoresDetalhe.filter((p) => p.convidado_em && !p.aceitou_em);
  const convitesVelhos = pendentes.filter((p) => {
    const d = daysSinceSp(p.convidado_em, now);
    return d != null && d >= cfg.convites_sem_aceite.dias;
  });
  if (convitesVelhos.length) {
    const nomes = convitesVelhos
      .map((p) => p.nome || p.convite_id || p.professor_id)
      .filter(Boolean)
      .slice(0, 8);
    alertas.push({
      chave: 'convites_sem_aceite',
      severidade: cfg.convites_sem_aceite.severidade,
      explicacao: `Convite de ${nomes.join(', ') || convitesVelhos.length + ' professor(es)'} enviado há ≥ ${cfg.convites_sem_aceite.dias} dias sem aceite.`,
      convites: convitesVelhos.map((p) => p.convite_id || p.professor_id).filter(Boolean),
    });
  } else if (
    !professoresDetalhe.length &&
    professoresCounts &&
    professoresCounts.convidados > professoresCounts.aceitos
  ) {
    const fonte = e.convidou_professores.quando || e.contratou.quando;
    const dias = fonte ? daysSinceSp(fonte, now) : null;
    if (dias != null && dias >= cfg.convites_sem_aceite.dias) {
      const n = professoresCounts.convidados - professoresCounts.aceitos;
      alertas.push({
        chave: 'convites_sem_aceite',
        severidade: cfg.convites_sem_aceite.severidade,
        explicacao: `${n} convite(s) sem aceite há ≥ ${dias} dia(s) (contagem do snapshot; o 139 não emitiu professor_convidar).`,
      });
    }
  }

  for (const p of professoresDetalhe) {
    if (!p.aceitou_em || p.primeiro_uso_em) continue;
    const dias = daysSinceSp(p.aceitou_em, now);
    if (dias != null && dias >= cfg.aceitou_nao_usou.dias) {
      alertas.push({
        chave: 'aceitou_nao_usou',
        severidade: cfg.aceitou_nao_usou.severidade,
        explicacao: `Professor ${p.nome || p.usuario_origem_ref || p.convite_id} aceitou há ${dias} dia(s) e ainda não usou o Inove.`,
      });
    }
  }

  if (teveUsoProf && ultimoUsoProf) {
    const dias = daysSinceSp(ultimoUsoProf, now);
    if (dias != null && dias >= cfg.parou_de_usar.dias) {
      alertas.push({
        chave: 'parou_de_usar',
        severidade: cfg.parou_de_usar.severidade,
        explicacao: `Conta teve uso de professor e está há ${dias} dia(s) sem evento de uso no Inove.`,
      });
    }
  }

  const total = asInt(licencas && licencas.total);
  const emUso = asInt(licencas && licencas.em_uso);
  const diasContrato = e.contratou.dias_desde;
  if (
    e.contratou.feito &&
    total > 0 &&
    diasContrato != null &&
    diasContrato >= cfg.licenca_ociosa.dias &&
    emUso / total < cfg.licenca_ociosa.razao
  ) {
    alertas.push({
      chave: 'licenca_ociosa',
      severidade: cfg.licenca_ociosa.severidade,
      explicacao: `Licenças em uso ${emUso}/${total} (${Math.round((emUso / total) * 100)}%) após ${diasContrato} dia(s) de contrato.`,
    });
  }

  const pontuacao = alertas.reduce(
    (acc, a) => acc + (PESO_SEVERIDADE[a.severidade] || 0),
    0
  );
  return { alertas, pontuacao };
}

function shapeConta(row, now = new Date(), limiares = LIMIARES) {
  const built = montarEtapas(row, now);
  const { alertas, pontuacao } = avaliarAlertas(
    {
      etapas: built.etapas,
      professoresDetalhe: row.professoresDetalhe || [],
      professoresCounts: built.professores,
      licencas: built.licencas,
      ultimoUsoProf: row.ultimo_uso_prof,
      teveUsoProf: asInt(row.n_prof_usando) > 0 || Boolean(row.primeiro_uso_prof),
    },
    now,
    limiares
  );
  const nome =
    String(row.identidade_nome || '').trim() ||
    nomeFromMeta(row.meta_json) ||
    String(row.instituicao_id);
  return {
    instituicao_id: String(row.instituicao_id),
    nome,
    contratou_em: iso(row.contratou_em),
    dias_de_contrato: row.contratou_em ? daysSinceSp(row.contratou_em, now) : null,
    etapa_atual: built.etapa_atual,
    etapa_atual_rotulo: (ETAPAS.find((x) => x.n === built.etapa_atual) || {}).rotulo || '—',
    etapas: built.etapas,
    professores: built.professores,
    licencas: built.licencas,
    alertas,
    pontuacao,
  };
}

function historicoDe(etapas) {
  return ETAPAS.map((def) => {
    const e = etapas[def.chave] || {};
    return {
      n: def.n,
      chave: def.chave,
      rotulo: def.rotulo,
      feito: Boolean(e.feito),
      quando: e.quando || null,
      dias_desde: e.dias_desde,
      fonte: e.fonte || null,
      quantidade: e.quantidade == null ? null : e.quantidade,
      quantidade_rotulo: e.quantidade_rotulo || null,
    };
  });
}

function mergeProfessores(eventRows, pessoaRows, now = new Date()) {
  const byKey = new Map();

  function ensure(key) {
    if (!byKey.has(key)) {
      byKey.set(key, {
        convite_id: null,
        professor_id: null,
        usuario_origem_ref: null,
        nome: null,
        convidado_em: null,
        aceitou_em: null,
        primeiro_uso_em: null,
        ultimo_uso_em: null,
        dias_sem_uso: null,
      });
    }
    return byKey.get(key);
  }

  for (const ev of eventRows || []) {
    const dados = ev.dados && typeof ev.dados === 'object' ? ev.dados : {};
    const cid = conviteIdOf(dados);
    const ref = ev.usuario_origem_ref ? String(ev.usuario_origem_ref) : null;
    const key = cid || (ev.tipo_evento === 'convite_escola_aceitar' && ref) || null;
    if (ev.tipo_evento === 'professor_convidar') {
      const row = ensure(cid || `ev:${iso(ev.criado_em)}`);
      row.convite_id = cid;
      row.professor_id = dados.professor_id != null ? String(dados.professor_id) : cid;
      if (!row.convidado_em || new Date(ev.criado_em) < new Date(row.convidado_em)) {
        row.convidado_em = iso(ev.criado_em);
      }
    } else if (ev.tipo_evento === 'convite_escola_aceitar') {
      const row = ensure(key || ref || `aceite:${iso(ev.criado_em)}`);
      row.convite_id = row.convite_id || cid;
      row.usuario_origem_ref = row.usuario_origem_ref || ref;
      if (ev.usuario_nome) row.nome = String(ev.usuario_nome);
      if (!row.aceitou_em || new Date(ev.criado_em) < new Date(row.aceitou_em)) {
        row.aceitou_em = iso(ev.criado_em);
      }
    }
  }

  for (const p of pessoaRows || []) {
    const ref = p.usuario_origem_ref ? String(p.usuario_origem_ref) : null;
    if (!ref || ref === 'sistema:snapshot') continue;
    let row = [...byKey.values()].find((x) => x.usuario_origem_ref === ref);
    if (!row) row = ensure(`ref:${ref}`);
    row.usuario_origem_ref = ref;
    if (p.nome) row.nome = String(p.nome);
    row.primeiro_uso_em = iso(p.primeiro_uso_em) || row.primeiro_uso_em;
    row.ultimo_uso_em = iso(p.ultimo_uso_em) || row.ultimo_uso_em;
    if (!row.aceitou_em && p.primeiro_acesso) {
      row.aceitou_em = iso(p.primeiro_acesso);
    }
  }

  return [...byKey.values()].map((p) => {
    const ancora = p.ultimo_uso_em || p.aceitou_em || p.convidado_em;
    return {
      ...p,
      dias_sem_uso: ancora ? daysSinceSp(ancora, now) : null,
    };
  });
}

const IDS_SQL = `
ids AS (
  SELECT instituicao_id FROM (
    SELECT DISTINCT instituicao_id
      FROM crm_sessoes
     WHERE instituicao_id IS NOT NULL
    UNION
    SELECT subject_id::uuid
      FROM contracts
     WHERE subject_type = 'instituicao'
       AND subject_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
  ) u
)`;

const LIST_SQL = `
  WITH ${IDS_SQL},
  contratos AS (
    SELECT DISTINCT ON (lower(c.subject_id))
      c.subject_id::uuid AS instituicao_id,
      c.created_at AS contratou_em,
      c.status AS contrato_status,
      c.meta_json,
      c.app_id
    FROM contracts c
    WHERE c.subject_type = 'instituicao'
      AND c.subject_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    ORDER BY lower(c.subject_id), c.created_at ASC
  ),
  seats AS (
    SELECT DISTINCT ON (lower(es.subject_id))
      es.subject_id::uuid AS instituicao_id,
      COALESCE((es.payload_json->>'seats')::int, (es.payload_json->>'seats_balance')::int) AS seats
    FROM entitlement_snapshots es
    WHERE es.subject_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    ORDER BY lower(es.subject_id), es.updated_at DESC NULLS LAST
  ),
  sistemas AS (
    SELECT instituicao_id, ARRAY_REMOVE(ARRAY_AGG(DISTINCT sistema_origem), NULL) AS sistemas
      FROM crm_sessoes
     WHERE instituicao_id IS NOT NULL
     GROUP BY instituicao_id
  ),
  ev AS (
    SELECT
      s.instituicao_id,
      MIN(e.criado_em) FILTER (
        WHERE e.tipo_evento = 'login_sucesso'
          AND s.sistema_origem = 'inove4us-school'
          AND COALESCE(s.usuario_origem_ref, '') <> 'sistema:snapshot'
      ) AS login_gestor,
      MIN(e.criado_em) FILTER (WHERE e.tipo_evento = 'senha_alterar') AS senha_alterar,
      MIN(e.criado_em) FILTER (WHERE e.tipo_evento = 'turma_criar') AS turma_criar,
      MIN(e.criado_em) FILTER (WHERE e.tipo_evento = 'aluno_matricular') AS aluno_matricular,
      MIN(e.criado_em) FILTER (WHERE e.tipo_evento = 'professor_convidar') AS primeiro_convidar,
      COUNT(*) FILTER (WHERE e.tipo_evento = 'professor_convidar')::int AS n_convidar,
      MIN(e.criado_em) FILTER (WHERE e.tipo_evento = 'convite_escola_aceitar') AS primeiro_aceite,
      COUNT(*) FILTER (WHERE e.tipo_evento = 'convite_escola_aceitar')::int AS n_aceitar,
      MIN(e.criado_em) FILTER (
        WHERE s.sistema_origem = 'inove4us'
          AND e.tipo_evento = ANY($1::text[])
          AND COALESCE(s.usuario_origem_ref, '') <> 'sistema:snapshot'
      ) AS primeiro_uso_prof,
      MAX(e.criado_em) FILTER (
        WHERE s.sistema_origem = 'inove4us'
          AND e.tipo_evento = ANY($1::text[])
          AND COALESCE(s.usuario_origem_ref, '') <> 'sistema:snapshot'
      ) AS ultimo_uso_prof,
      COUNT(DISTINCT s.usuario_origem_ref) FILTER (
        WHERE s.sistema_origem = 'inove4us'
          AND e.tipo_evento = ANY($1::text[])
          AND COALESCE(s.usuario_origem_ref, '') <> ''
          AND COALESCE(s.usuario_origem_ref, '') <> 'sistema:snapshot'
      )::int AS n_prof_usando,
      COUNT(DISTINCT (timezone('America/Sao_Paulo', e.criado_em))::date) FILTER (
        WHERE s.sistema_origem = 'inove4us'
          AND e.tipo_evento = ANY($1::text[])
          AND e.criado_em >= NOW() - INTERVAL '7 days'
          AND COALESCE(s.usuario_origem_ref, '') <> 'sistema:snapshot'
      )::int AS dias_uso_7d
    FROM crm_eventos e
    JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
    WHERE e.tipo_evento <> 'conta_snapshot'
      AND s.instituicao_id IS NOT NULL
    GROUP BY s.instituicao_id
  )
  SELECT
    i.instituicao_id,
    ident_i.nome AS identidade_nome,
    c.contratou_em,
    c.contrato_status,
    c.meta_json,
    c.app_id,
    seats.seats,
    ev.login_gestor,
    ev.senha_alterar,
    ev.turma_criar,
    ev.aluno_matricular,
    ev.primeiro_convidar,
    COALESCE(ev.n_convidar, 0) AS n_convidar,
    ev.primeiro_aceite,
    COALESCE(ev.n_aceitar, 0) AS n_aceitar,
    ev.primeiro_uso_prof,
    ev.ultimo_uso_prof,
    COALESCE(ev.n_prof_usando, 0) AS n_prof_usando,
    COALESCE(ev.dias_uso_7d, 0) AS dias_uso_7d,
    sis.sistemas,
    snap.snap_school
  FROM ids i
  LEFT JOIN crm_identidades ident_i
    ON ident_i.tipo = 'instituicao'
   AND ident_i.chave = i.instituicao_id::text
  LEFT JOIN contratos c ON c.instituicao_id = i.instituicao_id
  LEFT JOIN seats ON seats.instituicao_id = i.instituicao_id
  LEFT JOIN sistemas sis ON sis.instituicao_id = i.instituicao_id
  LEFT JOIN ev ON ev.instituicao_id = i.instituicao_id
  LEFT JOIN LATERAL (
    SELECT e.dados AS snap_school
      FROM crm_eventos e
      JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
     WHERE s.instituicao_id = i.instituicao_id
       AND e.tipo_evento = 'conta_snapshot'
       AND s.sistema_origem = 'inove4us-school'
       AND COALESCE(e.dados->>'escopo', '') <> 'professor'
     ORDER BY e.criado_em DESC
     LIMIT 1
  ) snap ON TRUE
`;

async function fetchPosVendaRows(pool) {
  const result = await pool.query(LIST_SQL, [USO_PROFESSOR]);
  return result.rows;
}

async function fetchProfessoresDetalhe(pool, instituicaoId) {
  const events = await pool.query(
    `
    SELECT e.tipo_evento, e.criado_em, e.dados, s.usuario_origem_ref, ident.nome AS usuario_nome
      FROM crm_eventos e
      JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
      LEFT JOIN crm_identidades ident
        ON ident.tipo = 'usuario'
       AND ident.chave = s.usuario_origem_ref
     WHERE s.instituicao_id = $1::uuid
       AND e.tipo_evento IN ('professor_convidar', 'convite_escola_aceitar')
     ORDER BY e.criado_em ASC
    `,
    [instituicaoId]
  );
  const pessoas = await pool.query(
    `
    SELECT
      s.usuario_origem_ref,
      ident.nome,
      MIN(s.criado_em) AS primeiro_acesso,
      MIN(e.criado_em) FILTER (WHERE e.tipo_evento = ANY($2::text[])) AS primeiro_uso_em,
      MAX(e.criado_em) FILTER (WHERE e.tipo_evento = ANY($2::text[])) AS ultimo_uso_em
    FROM crm_sessoes s
    JOIN crm_eventos e ON e.id_sessao = s.id_sessao
    LEFT JOIN crm_identidades ident
      ON ident.tipo = 'usuario'
     AND ident.chave = s.usuario_origem_ref
    WHERE s.instituicao_id = $1::uuid
      AND s.sistema_origem = 'inove4us'
      AND COALESCE(s.usuario_origem_ref, '') <> ''
      AND s.usuario_origem_ref <> 'sistema:snapshot'
      AND e.tipo_evento <> 'conta_snapshot'
    GROUP BY s.usuario_origem_ref, ident.nome
    `,
    [instituicaoId, USO_PROFESSOR]
  );
  return mergeProfessores(events.rows, pessoas.rows);
}

function registerCrmPosVendaRoutes(app, pool, auth) {
  const crmSecretAuthorized = auth && auth.crmSecretAuthorized;
  if (typeof crmSecretAuthorized !== 'function') {
    throw new Error('crm-pos-venda: crmSecretAuthorized é obrigatório');
  }

  app.get('/api/crm/pos-venda', async (req, res) => {
    if (!crmSecretAuthorized(req)) {
      return res.status(401).json({ ok: false, error: 'x-crm-secret inválido ou ausente' });
    }
    const alerta = String(req.query.alerta || '').trim().toLowerCase();
    if (alerta && !LIMIARES[alerta]) {
      return res.status(400).json({ ok: false, error: 'alerta desconhecido' });
    }
    const sistema = String(req.query.sistema || '').trim().toLowerCase();
    const desdeParsed = parseIsoParam(req.query.desde, 'desde');
    if (desdeParsed.error) {
      return res.status(400).json({ ok: false, error: desdeParsed.error });
    }

    const t0 = Date.now();
    try {
      const rows = await fetchPosVendaRows(pool);
      const now = new Date();
      let contas = rows.map((r) => shapeConta(r, now));
      if (sistema) {
        const byId = new Map(rows.map((r) => [String(r.instituicao_id), r]));
        contas = contas.filter((c) => {
          const src = byId.get(c.instituicao_id) || {};
          const sistemas = Array.isArray(src.sistemas) ? src.sistemas.map(String) : [];
          return sistemas.includes(sistema) || String(src.app_id || '') === sistema;
        });
      }
      if (desdeParsed.value) {
        const cut = desdeParsed.value.getTime();
        contas = contas.filter((c) => c.contratou_em && new Date(c.contratou_em).getTime() >= cut);
      }
      if (alerta) {
        contas = contas.filter((c) => (c.alertas || []).some((a) => a.chave === alerta));
      }
      contas.sort((a, b) => {
        if (b.pontuacao !== a.pontuacao) return b.pontuacao - a.pontuacao;
        const ta = a.contratou_em ? new Date(a.contratou_em).getTime() : 0;
        const tb = b.contratou_em ? new Date(b.contratou_em).getTime() : 0;
        return tb - ta;
      });
      const ms = Date.now() - t0;
      if (ms > 1000) {
        console.warn(`⚠️ [crm/pos-venda] consulta ${ms}ms (limiar 1s)`);
      }
      return res.json({
        ok: true,
        limiares: LIMIARES,
        contas,
        meta: { count: contas.length, elapsed_ms: ms },
      });
    } catch (err) {
      console.error('❌ [crm/pos-venda GET]', err.message);
      return res.status(500).json({ ok: false, error: 'Falha ao agregar pós-venda' });
    }
  });

  app.get('/api/crm/contas/:instituicao_id/pos-venda', async (req, res) => {
    if (!crmSecretAuthorized(req)) {
      return res.status(401).json({ ok: false, error: 'x-crm-secret inválido ou ausente' });
    }
    const raw = String(req.params.instituicao_id || '').trim();
    if (!UUID_RE.test(raw)) {
      return res.status(400).json({ ok: false, error: 'instituicao_id deve ser UUID válido' });
    }
    const instituicaoId = raw.toLowerCase();
    const t0 = Date.now();
    try {
      const rows = await fetchPosVendaRows(pool);
      const row = rows.find((r) => String(r.instituicao_id).toLowerCase() === instituicaoId);
      if (!row) {
        return res.status(404).json({ ok: false, error: 'conta não encontrada' });
      }
      const professores = await fetchProfessoresDetalhe(pool, instituicaoId);
      row.professoresDetalhe = professores;
      const now = new Date();
      const conta = shapeConta(row, now);
      const ms = Date.now() - t0;
      return res.json({
        ok: true,
        limiares: LIMIARES,
        instituicao_id: instituicaoId,
        ...conta,
        professores_detalhe: professores,
        historico: historicoDe(conta.etapas),
        meta: { elapsed_ms: ms },
      });
    } catch (err) {
      console.error('❌ [crm/contas/:id/pos-venda GET]', err.message);
      return res.status(500).json({ ok: false, error: 'Falha ao agregar pós-venda da conta' });
    }
  });
}

module.exports = {
  LIMIARES,
  PESO_SEVERIDADE,
  ETAPAS,
  USO_PROFESSOR,
  registerCrmPosVendaRoutes,
  montarEtapas,
  avaliarAlertas,
  shapeConta,
  mergeProfessores,
  daysSinceSp,
  historicoDe,
};
