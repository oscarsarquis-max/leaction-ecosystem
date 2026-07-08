import { useMemo } from "react";
import { Building2, Layers, Users } from "lucide-react";
import { BRAND_COLORS } from "../theme/brand";
import { extractPainelIndicadores } from "../utils/metricas";

function formatarScore(valor) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
    return "—";
  }

  return Number(valor).toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}

function CardKpi({ icone: Icone, rotulo, valor, detalhe, cor }) {
  return (
    <article className="card-panel flex items-start gap-3 p-4">
      <div
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
        style={{ backgroundColor: `${cor}18`, color: cor }}
      >
        <Icone className="h-5 w-5" strokeWidth={2} />
      </div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-cinza/70">
          {rotulo}
        </p>
        <p className="mt-1 text-2xl font-bold text-brand-verde">{valor}</p>
        {detalhe && <p className="mt-0.5 text-xs text-brand-cinza/60">{detalhe}</p>}
      </div>
    </article>
  );
}

function VisaoOrganizacao({ metricas, opcoes }) {
  const resumo = useMemo(() => {
    const colaboradores = opcoes.colaboradores || [];
    const setores = new Set(
      colaboradores.map((item) => item.codsetor).filter(Boolean)
    );

    const indicadores = extractPainelIndicadores(metricas, {
      nivel: "setor",
      busca: "",
    });

    const porSetor = new Map();
    colaboradores.forEach((item) => {
      const setor = item.codsetor || "—";
      porSetor.set(setor, (porSetor.get(setor) || 0) + 1);
    });

    return {
      totalColaboradores: colaboradores.length,
      totalSetores: setores.size || opcoes.setores?.length || 0,
      totalIndicadores: indicadores.length,
      totalMedicoes: metricas.length,
      indicadoresDestaque: indicadores.slice(0, 10),
      colaboradoresPorSetor: Array.from(porSetor.entries()).sort((a, b) =>
        a[0].localeCompare(b[0])
      ),
    };
  }, [metricas, opcoes]);

  return (
    <section id="visao-organizacao" className="space-y-6">
      <div className="rounded-xl border border-brand-verde/20 bg-brand-verde/5 px-4 py-3 text-sm text-brand-cinza">
        <strong className="text-brand-verde">Visão geral da organização</strong> — métricas
        consolidadas de todos os setores e colaboradores. Selecione um colaborador nos filtros
        ou nos atalhos APD para abrir a análise individual, cruzada e insights de IA.
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <CardKpi
          icone={Users}
          rotulo="Colaboradores"
          valor={resumo.totalColaboradores}
          detalhe="Com medições no período"
          cor={BRAND_COLORS.verde}
        />
        <CardKpi
          icone={Building2}
          rotulo="Setores"
          valor={resumo.totalSetores}
          cor={BRAND_COLORS.laranja}
        />
        <CardKpi
          icone={Layers}
          rotulo="Indicadores"
          valor={resumo.totalIndicadores}
          detalhe={`${resumo.totalMedicoes} medições`}
          cor={BRAND_COLORS.cinza}
        />
        <CardKpi
          icone={Layers}
          rotulo="Cobertura SPACE"
          valor="5 dim."
          detalhe="Satisfação · Performance · Atividade · Comunicação · Eficiência"
          cor="#1B6B47"
        />
      </div>

      {resumo.colaboradoresPorSetor.length > 0 && (
        <article className="card-panel overflow-hidden p-0">
          <div className="border-b border-gray-100 px-4 py-3 sm:px-5">
            <h4 className="text-sm font-semibold text-brand-verde">Colaboradores por setor</h4>
          </div>
          <div className="divide-y divide-gray-50">
            {resumo.colaboradoresPorSetor.map(([setor, quantidade]) => (
              <div
                key={setor}
                className="flex items-center justify-between px-4 py-2.5 text-sm sm:px-5"
              >
                <span className="font-medium text-brand-cinza">{setor}</span>
                <span className="rounded-full bg-brand-verde/10 px-2.5 py-0.5 text-xs font-semibold text-brand-verde">
                  {quantidade}
                </span>
              </div>
            ))}
          </div>
        </article>
      )}

      {resumo.indicadoresDestaque.length > 0 && (
        <article className="card-panel overflow-hidden p-0">
          <div className="border-b border-gray-100 px-4 py-3 sm:px-5">
            <h4 className="text-sm font-semibold text-brand-verde">
              Indicadores consolidados (organização)
            </h4>
            <p className="mt-0.5 text-xs text-brand-cinza/70">
              Média organizacional por código de indicador
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-surface/80 text-xs uppercase tracking-wide text-brand-cinza/70">
                  <th className="px-4 py-3 font-semibold sm:px-5">Código</th>
                  <th className="px-4 py-3 font-semibold sm:px-5">Indicador</th>
                  <th className="px-4 py-3 font-semibold sm:px-5">Dimensão</th>
                  <th className="px-4 py-3 text-right font-semibold sm:px-5">Score org.</th>
                  <th className="px-4 py-3 text-right font-semibold sm:px-5">Referencial</th>
                </tr>
              </thead>
              <tbody>
                {resumo.indicadoresDestaque.map((item) => (
                  <tr key={item.cod_indicador} className="border-b border-gray-50">
                    <td className="px-4 py-2.5 font-mono text-xs font-bold text-brand-verde sm:px-5">
                      {item.cod_indicador}
                    </td>
                    <td className="px-4 py-2.5 text-brand-cinza sm:px-5">{item.nome_metrica}</td>
                    <td className="px-4 py-2.5 text-xs text-brand-cinza/70 sm:px-5">
                      {item.dimensao || "—"}
                    </td>
                    <td className="px-4 py-2.5 text-right font-semibold text-brand-verde sm:px-5">
                      {formatarScore(item.score_selecionado)}
                    </td>
                    <td className="px-4 py-2.5 text-right text-brand-cinza sm:px-5">
                      {formatarScore(item.score_baseline)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      )}
    </section>
  );
}

export default VisaoOrganizacao;
