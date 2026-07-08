import { useMemo, useState } from 'react';

const TABS = [
  { id: 'dimensions', label: 'Dimensões' },
  { id: 'domains', label: 'Domínios' },
  { id: 'blocks', label: 'Blocos' },
  { id: 'deliverables', label: 'Entregáveis' },
];

function Field({ label, value, multiline = false }) {
  const display =
    value === null || value === undefined || value === ''
      ? '—'
      : typeof value === 'object'
        ? JSON.stringify(value, null, 2)
        : String(value);

  return (
    <div className="min-w-0">
      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
      {multiline ? (
        <dd className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-800">{display}</dd>
      ) : (
        <dd className="mt-1 break-words text-sm text-slate-800">{display}</dd>
      )}
    </div>
  );
}

function MetricsBlock({ metrics }) {
  if (!metrics) {
    return <p className="text-sm text-slate-500">Sem métricas associadas.</p>;
  }

  if (typeof metrics === 'string') {
    return (
      <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
        {metrics}
      </pre>
    );
  }

  if (Array.isArray(metrics)) {
    if (metrics.length === 0) {
      return <p className="text-sm text-slate-500">Sem métricas associadas.</p>;
    }
    return (
      <ul className="space-y-2">
        {metrics.map((metric, index) => (
          <li
            key={index}
            className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800"
          >
            {typeof metric === 'object' ? JSON.stringify(metric, null, 2) : String(metric)}
          </li>
        ))}
      </ul>
    );
  }

  if (typeof metrics === 'object') {
    return (
      <dl className="grid gap-2 sm:grid-cols-2">
        {Object.entries(metrics).map(([key, val]) => (
          <Field key={key} label={key} value={val} multiline />
        ))}
      </dl>
    );
  }

  return <Field label="Métrica" value={metrics} />;
}

export default function FrameworkTaxonomyExplorer({ taxonomy, loading = false }) {
  const [activeTab, setActiveTab] = useState('dimensions');
  const [filterDimensionId, setFilterDimensionId] = useState('');
  const [filterDomainId, setFilterDomainId] = useState('');
  const [filterBlockId, setFilterBlockId] = useState('');

  const counts = taxonomy?.counts || {};

  const dimensions = taxonomy?.dimensions || [];
  const domains = taxonomy?.domains || [];
  const blocks = taxonomy?.blocks || [];
  const deliverables = taxonomy?.deliverables || [];

  const filteredBlocks = useMemo(() => {
    return blocks.filter((block) => {
      if (filterDimensionId && block.dimension_id !== filterDimensionId) return false;
      if (filterDomainId && block.domain_id !== filterDomainId) return false;
      return true;
    });
  }, [blocks, filterDimensionId, filterDomainId]);

  const filteredDeliverables = useMemo(() => {
    if (!filterBlockId) return deliverables;
    return deliverables.filter((item) => item.block_id === filterBlockId);
  }, [deliverables, filterBlockId]);

  if (loading) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm text-slate-500">Carregando taxonomia PanelDX...</p>
      </section>
    );
  }

  if (!taxonomy) {
    return (
      <section className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-6 shadow-sm">
        <p className="text-sm text-slate-600">
          Taxonomia ainda não disponível para este framework.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-6 py-4">
        <h3 className="text-lg font-semibold text-slate-800">
          Constituição do Framework (PanelDX)
        </h3>
        <p className="mt-1 text-sm text-slate-500">
          {counts.dimensions ?? 0} dimensões · {counts.domains ?? 0} domínios ·{' '}
          {counts.blocks ?? 0} blocos · {counts.deliverables ?? 0} entregáveis
        </p>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-slate-100 px-6 py-3">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
              activeTab === tab.id
                ? 'bg-chameleon text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="p-6">
        {activeTab === 'dimensions' && (
          <div className="space-y-4">
            {dimensions.length === 0 ? (
              <p className="text-sm text-slate-500">Nenhuma dimensão persistida.</p>
            ) : (
              dimensions.map((dim) => (
                <article
                  key={dim.id}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-4"
                >
                  <p className="mb-3 text-xs font-bold uppercase tracking-wide text-chameleon-dark">
                    {dim.dimension_key || '—'} — {dim.name_dime}
                  </p>
                  <dl className="grid gap-3 sm:grid-cols-2">
                    <Field label="ID legado (id_dime)" value={dim.legacy_id_dime} />
                    <Field label="Chave" value={dim.dimension_key} />
                    <Field label="Código (code_dime)" value={dim.code_dime} />
                    <Field label="Ordem" value={dim.display_order} />
                    <Field label="Nome (name_dime)" value={dim.name_dime} />
                    <Field label="Perspectiva" value={dim.perspective_dime} />
                    <div className="sm:col-span-2">
                      <Field label="Descrição (desc_dime)" value={dim.desc_dime} multiline />
                    </div>
                    <div className="sm:col-span-2">
                      <Field
                        label="Descrição longa (long_description)"
                        value={dim.long_description}
                        multiline
                      />
                    </div>
                  </dl>
                </article>
              ))
            )}
          </div>
        )}

        {activeTab === 'domains' && (
          <div className="space-y-4">
            {domains.length === 0 ? (
              <p className="text-sm text-slate-500">Nenhum domínio persistido.</p>
            ) : (
              domains.map((dom) => (
                <article
                  key={dom.id}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-4"
                >
                  <p className="mb-3 text-xs font-bold uppercase tracking-wide text-chameleon-dark">
                    {dom.domain_key || '—'} — {dom.name_doma}
                  </p>
                  <dl className="grid gap-3 sm:grid-cols-2">
                    <Field label="ID legado (id_doma)" value={dom.legacy_id_doma} />
                    <Field label="Chave (domain_key)" value={dom.domain_key} />
                    <Field label="Ordem" value={dom.display_order} />
                    <Field label="Nome (name_doma)" value={dom.name_doma} />
                    <div className="sm:col-span-2">
                      <Field label="Descrição (desc_doma)" value={dom.desc_doma} multiline />
                    </div>
                    <div className="sm:col-span-2">
                      <Field
                        label="Vetor estratégico (vetor_estrategico)"
                        value={dom.vetor_estrategico}
                        multiline
                      />
                    </div>
                  </dl>
                </article>
              ))
            )}
          </div>
        )}

        {activeTab === 'blocks' && (
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Filtrar por dimensão</span>
                <select
                  value={filterDimensionId}
                  onChange={(e) => setFilterDimensionId(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-chameleon focus:ring-2 focus:ring-chameleon/20"
                >
                  <option value="">Todas as dimensões</option>
                  {dimensions.map((dim) => (
                    <option key={dim.id} value={dim.id}>
                      {dim.dimension_key} — {dim.name_dime}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Filtrar por domínio</span>
                <select
                  value={filterDomainId}
                  onChange={(e) => setFilterDomainId(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-chameleon focus:ring-2 focus:ring-chameleon/20"
                >
                  <option value="">Todos os domínios</option>
                  {domains.map((dom) => (
                    <option key={dom.id} value={dom.id}>
                      {dom.domain_key} — {dom.name_doma}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <p className="text-xs text-slate-500">
              {filteredBlocks.length} bloco(s) encontrado(s)
            </p>

            {filteredBlocks.length === 0 ? (
              <p className="text-sm text-slate-500">Nenhum bloco para os filtros selecionados.</p>
            ) : (
              filteredBlocks.map((block) => (
                <article
                  key={block.id}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-4"
                >
                  <p className="mb-3 text-xs font-bold uppercase tracking-wide text-chameleon-dark">
                    {block.legacy_id_bloc ?? '—'} — {block.name_bloc}
                  </p>
                  <dl className="grid gap-3 sm:grid-cols-2">
                    <Field label="ID legado (id_bloc)" value={block.legacy_id_bloc} />
                    <Field label="Nível (level_bloc)" value={block.level_bloc} />
                    <Field label="Dimensão" value={block.dimension_name} />
                    <Field label="Domínio" value={block.domain_name} />
                    <Field label="Chave dimensão" value={block.dimension_key} />
                    <Field label="Chave domínio" value={block.domain_key} />
                    <Field label="Qualificador (quali_bloc)" value={block.quali_bloc} />
                    <div className="sm:col-span-2">
                      <Field label="Nome (name_bloc)" value={block.name_bloc} />
                    </div>
                    <div className="sm:col-span-2">
                      <Field label="Descrição (desc_bloc)" value={block.desc_bloc} multiline />
                    </div>
                  </dl>
                </article>
              ))
            )}
          </div>
        )}

        {activeTab === 'deliverables' && (
          <div className="space-y-4">
            <label className="block max-w-xl">
              <span className="text-sm font-medium text-slate-700">Filtrar por bloco</span>
              <select
                value={filterBlockId}
                onChange={(e) => setFilterBlockId(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-chameleon focus:ring-2 focus:ring-chameleon/20"
              >
                <option value="">Todos os blocos</option>
                {blocks.map((block) => (
                  <option key={block.id} value={block.id}>
                    {block.legacy_id_bloc ?? '—'} — {block.name_bloc}
                  </option>
                ))}
              </select>
            </label>

            <p className="text-xs text-slate-500">
              {filteredDeliverables.length} entregável(is) encontrado(s)
            </p>

            {filteredDeliverables.length === 0 ? (
              <p className="text-sm text-slate-500">
                Nenhum entregável para o bloco selecionado.
              </p>
            ) : (
              filteredDeliverables.map((derv) => (
                <article
                  key={derv.id}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-4"
                >
                  <p className="mb-3 text-xs font-bold uppercase tracking-wide text-chameleon-dark">
                    {derv.legacy_id_derv ?? '—'} — {derv.name_derv}
                  </p>
                  <dl className="grid gap-3 sm:grid-cols-2">
                    <Field label="ID legado (id_derv)" value={derv.legacy_id_derv} />
                    <Field label="Bloco (id_bloc)" value={derv.legacy_id_bloc} />
                    <Field label="Nome do bloco" value={derv.block_name} />
                    <Field label="Nome (name_derv)" value={derv.name_derv} />
                    <div className="sm:col-span-2">
                      <Field label="Descrição (desc_derv)" value={derv.desc_derv} multiline />
                    </div>
                    <div className="sm:col-span-2">
                      <Field label="Definição (derv_defi)" value={derv.derv_defi} multiline />
                    </div>
                    <div className="sm:col-span-2">
                      <Field label="Composição (derv_comp)" value={derv.derv_comp} multiline />
                    </div>
                    <div className="sm:col-span-2">
                      <Field
                        label="Critérios DoD (criteria_dod)"
                        value={derv.criteria_dod}
                        multiline
                      />
                    </div>
                  </dl>
                  <div className="mt-4 border-t border-slate-200 pt-4">
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Métricas associadas (derv_metr)
                    </p>
                    <MetricsBlock metrics={derv.derv_metr} />
                  </div>
                </article>
              ))
            )}
          </div>
        )}
      </div>
    </section>
  );
}
