package br.com.segsense.application.demo;

import br.com.segsense.domain.demo.DemoProtectionException;
import java.util.List;
import java.util.Optional;

public final class GovernedDemoSourceRegistry {

  public static final String FAMILY_ID = "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1";
  public static final String INCOME_ID = "SEGSENSE_INCOME_INTERRUPTION_SYNTHETIC_V1";
  public static final String FIRES_ID = "SEGSENSE_NEARBY_FIRES_SYNTHETIC_V1";
  public static final String REVOKED_ID = "SEGSENSE_REVOKED_SYNTHETIC_V1";

  private static final List<GovernedDemoSource> SOURCES =
      List.of(
          new GovernedDemoSource(
              FAMILY_ID,
              "continuidade-familiar",
              "Continuidade financeira da família (sintético)",
              "Registro editorial SegSense",
              "demo-editorial-v1",
              "2026-09-13T12:00:00Z",
              "family_continuity",
              "dependents_need_continuity",
              "understand_options",
              "years",
              "no_quote",
              "Famílias organizam a vida em torno da renda de quem trabalha. Um evento inesperado pode interromper essa continuidade. Texto sintético autorizado; não é artigo integral.",
              false),
          new GovernedDemoSource(
              INCOME_ID,
              "interrupcao-renda",
              "Interrupção da renda do trabalho (sintético)",
              "Registro editorial SegSense",
              "demo-income-v1",
              "2026-09-14T12:00:00Z",
              "income_interruption",
              "income_gap_if_work_stops",
              "compare_gaps",
              "months",
              "no_quote",
              "Se o trabalho para, a renda mensal pode cessar enquanto contas continuam. Texto sintético autorizado; não é artigo integral.",
              false),
          new GovernedDemoSource(
              FIRES_ID,
              "proximidade-incendios",
              "Incêndios próximos de uma região hipotética (sintético)",
              "Registro editorial SegSense",
              "demo-fires-v1",
              "2026-09-14T12:00:00Z",
              "nearby_fires",
              "nearby_fires_hypothetical_region",
              "simulate_home_quote",
              "months",
              "editorial_not_risk",
              "Em uma região hipotética, relatos descrevem incêndios em áreas próximas. O texto é editorial e sintético. Não prova que um imóvel específico está exposto, não autoriza inferir endereço e não agrava preço.",
              false),
          new GovernedDemoSource(
              REVOKED_ID,
              "revogada",
              "Fonte sintética revogada",
              "Registro editorial SegSense",
              "demo-revoked-v1",
              "2026-09-01T12:00:00Z",
              "family_continuity",
              "dependents_need_continuity",
              "understand_options",
              "years",
              "no_quote",
              "Esta fonte foi revogada e não pode originar contexto.",
              true));

  private GovernedDemoSourceRegistry() {}

  public static List<GovernedDemoSource> listPublic() {
    return SOURCES;
  }

  public static GovernedDemoSource requireLive(String slug) {
    GovernedDemoSource source =
        SOURCES.stream()
            .filter(item -> item.slug().equals(slug))
            .findFirst()
            .orElseThrow(
                () ->
                    new DemoProtectionException(
                        "UNKNOWN_CONTEXT_SOURCE", 400, "O link não está no registro de fontes governadas desta demonstração."));
    if (source.revoked()) {
      throw new DemoProtectionException(
          "REVOKED_CONTEXT_SOURCE", 409, "Esta fonte governada foi revogada e não pode ser usada.");
    }
    return source;
  }

  public static Optional<GovernedDemoSource> findById(String id) {
    return SOURCES.stream().filter(item -> item.id().equals(id)).findFirst();
  }

  public static GovernedDemoSource family() {
    return requireLive("continuidade-familiar");
  }
}
