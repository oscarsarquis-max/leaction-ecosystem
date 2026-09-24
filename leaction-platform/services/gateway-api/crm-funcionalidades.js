'use strict';

/**
 * Taxonomia de funcionalidades do Sponge (prompt 138).
 * Único arquivo a editar quando a classificação mudar.
 *
 * Cada evento cai em exatamente uma funcionalidade do mesmo sistema_origem.
 * tipo_evento conta_snapshot fica fora (filtrado antes).
 * O que não casar → chave `outros`.
 */

/** Intervalo máximo atribuído a uma ação. Acima disso = inatividade (não conta). */
const TETO_INATIVIDADE_MS = 10 * 60 * 1000;

const FUNCIONALIDADES = [
  // —— Inove4us ————————————————————————————————————————————————
  {
    chave: 'dia_a_dia',
    rotulo: 'Dia a Dia (aula diária)',
    sistema: 'inove4us',
    tipos: [
      'aula_*',
      'roteiro_*',
      'metodologia_aplicar',
      'conteudo_sugerido_gerar',
    ],
    paginas: ['/dia-a-dia', '/execucao'],
  },
  {
    chave: 'desafio',
    rotulo: 'Desafio (Mesa, EduScrum)',
    sistema: 'inove4us',
    tipos: ['desafio_*', 'caminho_selecionar'],
    paginas: ['/desafio', '/desafios'],
  },
  {
    chave: 'wizard_ia',
    rotulo: 'Wizard / geração por IA',
    sistema: 'inove4us',
    tipos: ['wizard_gerar', 'plano_gerar', 'ia_fallback'],
    paginas: [],
  },
  {
    chave: 'kanban',
    rotulo: 'Kanban',
    sistema: 'inove4us',
    tipos: ['kanban_card_*'],
    paginas: [],
  },
  {
    chave: 'pei_aee',
    rotulo: 'PEI/AEE (professor)',
    sistema: 'inove4us',
    tipos: ['pei_aplicar'],
    paginas: [],
  },
  {
    chave: 'agenda',
    rotulo: 'Agenda',
    sistema: 'inove4us',
    tipos: ['agenda_evento_criar'],
    paginas: [],
  },
  {
    chave: 'creditos',
    rotulo: 'Créditos de IA',
    sistema: 'inove4us',
    tipos: ['credito_consumir'],
    paginas: [],
  },
  {
    chave: 'comercial',
    rotulo: 'Checkout/pagamento',
    sistema: 'inove4us',
    tipos: ['checkout_*', 'pagamento_*'],
    paginas: ['/planos', '/plans', '/pagamento'],
  },
  {
    chave: 'acesso',
    rotulo: 'Acesso/Home',
    sistema: 'inove4us',
    tipos: ['login_sucesso', 'convite_escola_aceitar'],
    paginas: ['/acesso', '/mesa-do-inovador', '/'],
  },
  // —— School ————————————————————————————————————————————————
  {
    chave: 'secretaria',
    rotulo: 'Secretaria',
    sistema: 'inove4us-school',
    tipos: [
      'turma_criar',
      'aluno_matricular',
      'professor_cadastrar',
      'professor_convidar',
      'convite_revogar',
      'alocacao_*',
    ],
    paginas: ['/secretaria'],
  },
  {
    chave: 'pei_aee_gestor',
    rotulo: 'PEI/AEE (editor pedagógico)',
    sistema: 'inove4us-school',
    tipos: ['aee_condicao_*', 'pei_criar', 'pei_atualizar', 'pei_assinar'],
    paginas: ['/editor-pedagogico'],
  },
  {
    chave: 'comunicados',
    rotulo: 'Comunicados',
    sistema: 'inove4us-school',
    tipos: ['comunicado_publicar'],
    paginas: [],
  },
  {
    chave: 'equipe',
    rotulo: 'Equipe/convites',
    sistema: 'inove4us-school',
    tipos: [],
    paginas: ['/equipe'],
  },
  {
    chave: 'comercial',
    rotulo: 'Checkout/licenças',
    sistema: 'inove4us-school',
    tipos: ['checkout_*', 'pagamento_*'],
    paginas: ['/market'],
  },
  {
    chave: 'acesso',
    rotulo: 'Acesso/Home',
    sistema: 'inove4us-school',
    tipos: ['login_sucesso', 'senha_alterar'],
    paginas: ['/acesso', '/'],
  },
  // —— Loja de Pães — pageview entra por tipo literal, sem páginas (o 145 nomeia as rotas).
  {
    chave: 'vitrine',
    rotulo: 'Vitrine',
    sistema: 'lojadepaes',
    tipos: ['pageview', 'fornada_escolher', 'data_solicitar'],
    paginas: [],
  },
  {
    chave: 'pedido',
    rotulo: 'Pedido',
    sistema: 'lojadepaes',
    tipos: ['pedido_enviar', 'pedido_aceitar'],
    paginas: [],
  },
  {
    chave: 'financeiro',
    rotulo: 'Financeiro',
    sistema: 'lojadepaes',
    tipos: ['pagamento_registrar'],
    paginas: [],
  },
];

const OUTROS = {
  chave: 'outros',
  rotulo: 'Não mapeado',
  sistema: null,
};

function tipoCasa(tipo, regra) {
  const t = String(tipo || '').toLowerCase();
  const r = String(regra || '').toLowerCase();
  if (!t || !r) return false;
  if (r.endsWith('*')) return t.startsWith(r.slice(0, -1));
  return t === r;
}

function normalizarPath(url) {
  let raw = String(url || '').trim();
  if (!raw) return '';
  if (/^https?:\/\//i.test(raw)) {
    try {
      raw = new URL(raw).pathname || '/';
    } catch {
      /* keep raw */
    }
  }
  let path = raw.split('?')[0].split('#')[0].toLowerCase();
  if (!path.startsWith('/')) path = `/${path}`;
  if (path.length > 1 && path.endsWith('/')) path = path.slice(0, -1);
  return path || '/';
}

function paginaCasa(path, padrao) {
  const p = String(path || '');
  let pat = String(padrao || '').toLowerCase();
  if (!p || !pat) return false;
  if (pat.length > 1 && pat.endsWith('/')) pat = pat.slice(0, -1);
  if (pat === '/') return p === '/';
  return p === pat || p.startsWith(`${pat}/`);
}

function catalogoDoSistema(sistema) {
  const s = String(sistema || '');
  return FUNCIONALIDADES.filter((f) => f.sistema === s);
}

/**
 * @returns {{ chave: string, rotulo: string, sistema: string|null, mapeado: boolean }}
 */
function classificarEvento(row) {
  const tipo = String(row.tipo_evento || '').toLowerCase();
  if (tipo === 'conta_snapshot') {
    return { chave: null, rotulo: null, sistema: null, mapeado: false, excluido: true };
  }
  const sistema = String(row.sistema_origem || '');
  const catalogo = catalogoDoSistema(sistema);
  if (tipo && tipo !== 'pageview') {
    for (const feat of catalogo) {
      if ((feat.tipos || []).some((regra) => tipoCasa(tipo, regra))) {
        return {
          chave: feat.chave,
          rotulo: feat.rotulo,
          sistema: feat.sistema,
          mapeado: true,
        };
      }
    }
  }
  if (tipo === 'pageview') {
    for (const feat of catalogo) {
      if ((feat.tipos || []).some((regra) => regra === 'pageview')) {
        return {
          chave: feat.chave,
          rotulo: feat.rotulo,
          sistema: feat.sistema,
          mapeado: true,
        };
      }
    }
  }
  if (tipo === 'pageview' || !tipo) {
    const path = normalizarPath(row.url_pagina);
    for (const feat of catalogo) {
      if ((feat.paginas || []).some((pat) => paginaCasa(path, pat))) {
        return {
          chave: feat.chave,
          rotulo: feat.rotulo,
          sistema: feat.sistema,
          mapeado: true,
        };
      }
    }
  }
  return {
    chave: OUTROS.chave,
    rotulo: OUTROS.rotulo,
    sistema: sistema || null,
    mapeado: false,
  };
}

function roundPct(part, total) {
  const p = Number(part) || 0;
  const t = Number(total) || 0;
  if (t <= 0) return 0;
  return Math.round((p / t) * 1000) / 10;
}

/** Ajusta décimos para a soma fechar em 100.0 (maior resto). */
function pctsFecham100(parts, total) {
  const n = parts.length;
  if (n === 0 || !total || total <= 0) return parts.map(() => 0);
  const exact = parts.map((p) => (Number(p) / total) * 100);
  const tenths = exact.map((x) => Math.floor(x * 10 + 1e-9));
  let used = tenths.reduce((a, b) => a + b, 0);
  let rem = 1000 - used;
  const order = exact
    .map((x, i) => ({ i, frac: x * 10 - tenths[i], val: Number(parts[i]) }))
    .filter((x) => x.val > 0)
    .sort((a, b) => b.frac - a.frac || b.val - a.val);
  let k = 0;
  while (rem > 0 && order.length) {
    tenths[order[k % order.length].i] += 1;
    rem -= 1;
    k += 1;
  }
  while (rem < 0 && order.length) {
    const idx = order[(order.length + rem) % order.length].i;
    if (tenths[idx] > 0) {
      tenths[idx] -= 1;
      rem += 1;
    } else {
      break;
    }
  }
  return tenths.map((t) => t / 10);
}

function pessoaKey(ref) {
  const r = String(ref || '').trim();
  return r || null;
}

function featureKey(chave, sistema) {
  return `${chave}\u0000${sistema || ''}`;
}

function emptyBucket(meta) {
  return {
    chave: meta.chave,
    rotulo: meta.rotulo,
    sistema: meta.sistema,
    eventos: 0,
    pessoas: new Set(),
    sessoes: new Set(),
    tempo_s: 0,
  };
}

function shapeBucket(bucket, totais) {
  const eventos = bucket.eventos;
  const pessoas = bucket.pessoas.size;
  const sessoes = bucket.sessoes.size;
  const tempoS = Math.round(bucket.tempo_s * 10) / 10;
  return {
    chave: bucket.chave,
    rotulo: bucket.rotulo,
    sistema: bucket.sistema,
    eventos,
    pct_eventos: roundPct(eventos, totais.eventos),
    pessoas,
    pct_pessoas: roundPct(pessoas, totais.pessoas),
    sessoes,
    pct_sessoes: roundPct(sessoes, totais.sessoes),
    tempo_s: tempoS,
    pct_tempo: roundPct(tempoS, totais.tempo_s),
    tempo_medio_por_sessao_s:
      sessoes > 0 ? Math.round((tempoS / sessoes) * 10) / 10 : 0,
  };
}

/**
 * @param {Array<{id_sessao:string, sistema_origem:string, usuario_origem_ref?:string|null, tipo_evento:string, url_pagina?:string, criado_em: Date|string}>} events
 * @param {{ agruparDia?: boolean, topOutros?: number }} [opts]
 */
function computeUso(events, opts) {
  const agruparDia = Boolean(opts && opts.agruparDia);
  const topOutros = (opts && opts.topOutros) || 12;
  const mapped = new Map();
  const outros = emptyBucket(OUTROS);
  outros.tipos = new Map();
  outros.paginas = new Map();
  const bySessao = new Map();
  const serieMap = new Map();

  const classified = [];
  for (const row of events) {
    const cls = classificarEvento(row);
    if (cls.excluido) continue;
    classified.push({ row, cls });
  }

  for (const { row, cls } of classified) {
    const sessao = String(row.id_sessao);
    const pessoa = pessoaKey(row.usuario_origem_ref);
    let bucket;
    if (cls.mapeado) {
      const k = featureKey(cls.chave, cls.sistema);
      if (!mapped.has(k)) {
        mapped.set(k, emptyBucket(cls));
      }
      bucket = mapped.get(k);
    } else {
      bucket = outros;
      const tipo = String(row.tipo_evento || 'pageview');
      outros.tipos.set(tipo, (outros.tipos.get(tipo) || 0) + 1);
      const path = normalizarPath(row.url_pagina) || '(sem página)';
      outros.paginas.set(path, (outros.paginas.get(path) || 0) + 1);
    }
    bucket.eventos += 1;
    bucket.sessoes.add(sessao);
    if (pessoa) bucket.pessoas.add(pessoa);

    if (!bySessao.has(sessao)) bySessao.set(sessao, []);
    bySessao.get(sessao).push({ row, cls, bucket });

    if (agruparDia) {
      const stamp = row.criado_em instanceof Date ? row.criado_em : new Date(row.criado_em);
      const day = Number.isNaN(stamp.getTime())
        ? 'unknown'
        : stamp.toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' });
      const sk = `${day}\u0000${cls.chave}\u0000${cls.sistema || ''}`;
      if (!serieMap.has(sk)) {
        serieMap.set(sk, {
          data: day,
          chave: cls.chave,
          rotulo: cls.rotulo,
          sistema: cls.sistema,
          eventos: 0,
          pessoas: new Set(),
        });
      }
      const s = serieMap.get(sk);
      s.eventos += 1;
      if (pessoa) s.pessoas.add(pessoa);
    }
  }

  for (const list of bySessao.values()) {
    list.sort((a, b) => {
      const ta = new Date(a.row.criado_em).getTime();
      const tb = new Date(b.row.criado_em).getTime();
      if (ta !== tb) return ta - tb;
      return Number(a.row.id || 0) - Number(b.row.id || 0);
    });
    for (let i = 0; i < list.length - 1; i += 1) {
      const t0 = new Date(list[i].row.criado_em).getTime();
      const t1 = new Date(list[i + 1].row.criado_em).getTime();
      const dt = t1 - t0;
      if (dt > 0 && dt <= TETO_INATIVIDADE_MS) {
        list[i].bucket.tempo_s += dt / 1000;
      }
    }
  }

  const pessoasRecorte = new Set();
  const sessoesRecorte = new Set();
  let eventosRecorte = 0;
  for (const { row } of classified) {
    eventosRecorte += 1;
    sessoesRecorte.add(String(row.id_sessao));
    const pessoa = pessoaKey(row.usuario_origem_ref);
    if (pessoa) pessoasRecorte.add(pessoa);
  }

  let tempoTotal = 0;
  for (const b of mapped.values()) tempoTotal += b.tempo_s;
  tempoTotal += outros.tempo_s;

  const totais = {
    eventos: eventosRecorte,
    pessoas: pessoasRecorte.size,
    sessoes: sessoesRecorte.size,
    tempo_s: Math.round(tempoTotal * 10) / 10,
  };

  const funcionalidades = [...mapped.values()]
    .map((b) => shapeBucket(b, totais))
    .sort(
      (a, b) =>
        b.pct_tempo - a.pct_tempo ||
        b.eventos - a.eventos ||
        a.rotulo.localeCompare(b.rotulo, 'pt-BR')
    );

  const topList = (mapa) =>
    [...mapa.entries()]
      .sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])))
      .slice(0, topOutros)
      .map(([valor, count]) => ({ valor, count }));

  const outrosShaped = shapeBucket(outros, totais);
  const mixEventos = [...funcionalidades.map((f) => f.eventos), outrosShaped.eventos];
  const mixTempo = [...funcionalidades.map((f) => f.tempo_s), outrosShaped.tempo_s];
  const pctEv = pctsFecham100(mixEventos, totais.eventos);
  const pctTm = pctsFecham100(mixTempo, totais.tempo_s);
  funcionalidades.forEach((f, i) => {
    f.pct_eventos = pctEv[i];
    f.pct_tempo = pctTm[i];
  });
  outrosShaped.pct_eventos = pctEv[pctEv.length - 1];
  outrosShaped.pct_tempo = pctTm[pctTm.length - 1];
  funcionalidades.sort(
    (a, b) =>
      b.pct_tempo - a.pct_tempo ||
      b.eventos - a.eventos ||
      a.rotulo.localeCompare(b.rotulo, 'pt-BR')
  );

  const outrosOut = {
    ...outrosShaped,
    tipos_frequentes: topList(outros.tipos).map((x) => ({
      tipo_evento: x.valor,
      count: x.count,
    })),
    paginas_frequentes: topList(outros.paginas).map((x) => ({
      url: x.valor,
      count: x.count,
    })),
  };

  const result = { totais, funcionalidades, outros: outrosOut };
  if (agruparDia) {
    result.serie = [...serieMap.values()]
      .map((s) => ({
        data: s.data,
        chave: s.chave,
        rotulo: s.rotulo,
        sistema: s.sistema,
        eventos: s.eventos,
        pessoas: s.pessoas.size,
      }))
      .sort(
        (a, b) =>
          a.data.localeCompare(b.data) ||
          a.chave.localeCompare(b.chave) ||
          String(a.sistema || '').localeCompare(String(b.sistema || ''))
      );
  }
  return result;
}

module.exports = {
  TETO_INATIVIDADE_MS,
  FUNCIONALIDADES,
  OUTROS,
  classificarEvento,
  computeUso,
  normalizarPath,
};
