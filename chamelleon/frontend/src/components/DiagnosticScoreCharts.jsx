import DimensionComparisonChart from './DimensionComparisonChart';
import DomainChartsGrid from './DomainChartsGrid';

export default function DiagnosticScoreCharts({
  scoresPresente,
  scoresFuturo,
  scoresGap,
  scoresSetorialPresente,
  sectorDimensionLabel,
  sectorLegendLabel,
}) {
  const hasCharts =
    scoresPresente?.pdim_scores && Object.keys(scoresPresente.pdim_scores).length > 0;

  if (!hasCharts) return null;

  return (
    <div className="space-y-6">
      <DimensionComparisonChart
        scoresPresente={scoresPresente}
        scoresFuturo={scoresFuturo}
        scoresGap={scoresGap}
        scoresSetorialPresente={scoresSetorialPresente}
        sectorDimensionLabel={sectorDimensionLabel}
        sectorLegendLabel={sectorLegendLabel}
      />
      <DomainChartsGrid
        scoresPresente={scoresPresente}
        scoresFuturo={scoresFuturo}
        scoresGap={scoresGap}
        scoresSetorialPresente={scoresSetorialPresente}
        sectorDimensionLabel={sectorDimensionLabel}
        sectorLegendLabel={sectorLegendLabel}
      />
    </div>
  );
}
