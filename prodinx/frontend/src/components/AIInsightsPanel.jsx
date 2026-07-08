import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  Bot,
  Lightbulb,
  Sparkles,
} from "lucide-react";
import { fetchAnaliseInteligente } from "../api/client";
import { getOrganizacaoNome } from "../config/organizacao";
import { BRAND_COLORS } from "../theme/brand";

function SkeletonLinha({ largura = "w-full" }) {
  return (
    <div
      className={`h-3 rounded-md bg-gradient-to-r from-gray-200 via-white to-gray-200 bg-[length:200%_100%] animate-shimmer ${largura}`}
    />
  );
}

function PainelCarregando() {
  return (
    <div className="card-panel flex h-full flex-col gap-5 p-5">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-verde/10">
          <Bot className="h-5 w-5 animate-pulse text-brand-verde" strokeWidth={2} />
        </div>
        <div className="flex-1 space-y-2">
          <SkeletonLinha largura="w-2/3" />
          <SkeletonLinha largura="w-1/2" />
        </div>
      </div>

      <div className="flex items-center gap-2 rounded-lg border border-brand-laranja/20 bg-brand-laranja/5 px-3 py-2 text-xs font-medium text-brand-verde">
        <Sparkles className="h-4 w-4 animate-pulse text-brand-laranja" strokeWidth={2} />
        IA processando métricas...
      </div>

      {[1, 2, 3].map((item) => (
        <div
          key={item}
          className="space-y-3 rounded-xl border border-gray-100 bg-surface/80 p-4 animate-pulse"
        >
          <SkeletonLinha largura="w-3/4" />
          <SkeletonLinha />
          <SkeletonLinha largura="w-5/6" />
          <div className="h-14 rounded-lg bg-gradient-to-r from-amber-50 via-white to-amber-50 bg-[length:200%_100%] animate-shimmer" />
        </div>
      ))}
    </div>
  );
}

function CardRecomendacao({ item }) {
  const isAlerta = item.tipo !== "oportunidade";
  const Icone = isAlerta ? AlertTriangle : Lightbulb;
  const corIcone = isAlerta ? BRAND_COLORS.vermelho : BRAND_COLORS.laranja;
  const fundoAcao = isAlerta ? "bg-amber-50 border-amber-200" : "bg-emerald-50 border-emerald-200";

  return (
    <article className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex gap-3">
        <div
          className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
          style={{ backgroundColor: `${corIcone}14`, color: corIcone }}
        >
          <Icone className="h-4 w-4" strokeWidth={2.25} />
        </div>
        <div className="min-w-0 flex-1 space-y-3">
          <h4 className="text-sm font-bold leading-snug text-brand-verde">{item.titulo}</h4>
          <p className="text-sm leading-relaxed text-brand-cinza/85">{item.analise_cruzada}</p>
          {item.acao_sugerida && (
            <div className={`rounded-lg border px-3 py-2.5 ${fundoAcao}`}>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-brand-cinza/70">
                Ação sugerida · 1-on-1
              </p>
              <p className="mt-1 text-sm font-medium leading-relaxed text-brand-cinza">
                {item.acao_sugerida}
              </p>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

function AIInsightsPanel({ idColaborador, colaboradorNome }) {
  const [dados, setDados] = useState(null);
  const [loading, setLoading] = useState(false);
  const [regenerando, setRegenerando] = useState(false);
  const [erro, setErro] = useState(null);

  const carregarAnalise = useCallback(
    async ({ regenerar = false } = {}) => {
      if (!idColaborador) {
        setDados(null);
        setErro(null);
        return;
      }

      try {
        if (regenerar) {
          setRegenerando(true);
        } else {
          setLoading(true);
        }
        setErro(null);
        if (regenerar) {
          setDados(null);
        }
        const resposta = await fetchAnaliseInteligente(idColaborador, { regenerar });
        setDados(resposta);
      } catch (err) {
        setErro(
          err.response?.data?.erro ||
            "Não foi possível gerar a análise inteligente. Verifique o serviço AWS Bedrock."
        );
        if (regenerar) {
          setDados(null);
        }
      } finally {
        setLoading(false);
        setRegenerando(false);
      }
    },
    [idColaborador]
  );

  useEffect(() => {
    carregarAnalise();
  }, [carregarAnalise]);

  if (!idColaborador) {
    return (
      <aside className="card-panel flex min-h-[320px] items-center justify-center p-6 text-center text-sm text-brand-cinza/70">
        Selecione um colaborador para gerar insights de IA.
      </aside>
    );
  }

  if (loading || regenerando) {
    return <PainelCarregando />;
  }

  const origemCache = dados?.origem === "cache";

  return (
    <aside className="card-panel flex h-full flex-col gap-4 p-5">
      <header className="space-y-1 border-b border-gray-100 pb-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-verde text-white">
              <Bot className="h-4 w-4" strokeWidth={2} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-brand-verde">
                Insights IA · {getOrganizacaoNome()}
              </h3>
              <p className="text-xs text-brand-cinza/70">
                {origemCache ? "Recuperado do histórico" : "Claude via AWS Bedrock"}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => carregarAnalise({ regenerar: true })}
            disabled={regenerando}
            className="shrink-0 rounded-lg border border-brand-verde/30 px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-brand-verde transition hover:bg-brand-verde/5 disabled:opacity-50"
          >
            {regenerando ? "Regenerando..." : "Regenerar"}
          </button>
        </div>
        {colaboradorNome && (
          <p className="text-xs font-medium text-brand-cinza">{colaboradorNome}</p>
        )}
      </header>

      {erro && (
        <div className="rounded-lg border border-brand-vermelho/30 bg-brand-vermelho/10 px-3 py-2 text-xs text-brand-vermelho">
          {erro}
          <button
            type="button"
            onClick={() => carregarAnalise({ regenerar: true })}
            className="ml-2 font-semibold underline underline-offset-2"
          >
            Tentar novamente
          </button>
        </div>
      )}

      {dados?.recomendacoes?.length > 0 && (
        <div className="space-y-3 overflow-y-auto pr-1 max-h-[min(72vh,720px)]">
          {dados.recomendacoes.map((item) => (
            <CardRecomendacao key={item.id} item={item} />
          ))}
        </div>
      )}

      {dados?.gerado_em && (
        <p className="mt-auto border-t border-gray-100 pt-3 text-[10px] text-brand-cinza/50">
          Gerado em {new Date(dados.gerado_em).toLocaleString("pt-BR")}
        </p>
      )}
    </aside>
  );
}

export default AIInsightsPanel;
