import GraficosAnaliseCruzada from "./GraficosAnaliseCruzada";
import AIInsightsPanel from "./AIInsightsPanel";

function AnaliseCruzada({
  idColaborador,
  colaboradorNome,
  scoresDimensoes,
  memoriaCalculo,
}) {
  if (!idColaborador) {
    return null;
  }

  return (
    <section id="analise-cruzada" className="space-y-4">
      <div>
        <h3 className="section-title">Análise Cruzada · Individual vs. Equipe</h3>
        <p className="section-subtitle">
          Gráficos de discrepância e recomendações da IA para a próxima reunião de 1-on-1.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,380px)] xl:items-start">
        <GraficosAnaliseCruzada
          scoresDimensoes={scoresDimensoes}
          memoriaCalculo={memoriaCalculo}
        />
        <AIInsightsPanel
          idColaborador={idColaborador}
          colaboradorNome={colaboradorNome}
        />
      </div>
    </section>
  );
}

export default AnaliseCruzada;
