package br.com.banco.spider.operational.failurelab;

import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;

/**
 * Constrói o pacote de evidência segura. O digest cobre apenas o resumo estável da execução
 * controlada — nunca payload, credencial ou conteúdo de negócio.
 */
public class FailureLabEvidenceService {

  private final SpiderClock clock;
  private final IdentifierGenerator ids;

  public FailureLabEvidenceService(SpiderClock clock, IdentifierGenerator ids) {
    this.clock = clock;
    this.ids = ids;
  }

  public FailureLabEvidenceBundle build(FailureLabRun run, FailureScenarioDefinition scenario) {
    boolean complete =
        run.verificationResults().stream()
            .noneMatch(
                result ->
                    result.status() == VerificationStatus.NOT_APPLICABLE
                        || result.status() == VerificationStatus.INCONCLUSIVE);
    return new FailureLabEvidenceBundle(
        FailureLabEvidenceBundle.SCHEMA_VERSION,
        ids.nextId("labev"),
        run.labRunId(),
        scenario.ref(),
        run.boundary(),
        clock.now(),
        run.executionRefs(),
        run.verificationResults(),
        FailureLabEvidenceBundle.REDACTION_APPLIED,
        complete ? FailureLabEvidenceBundle.COMPLETE : FailureLabEvidenceBundle.PARTIAL,
        digest(run));
  }

  static String digest(FailureLabRun run) {
    List<String> statuses =
        run.verificationResults().stream()
            .map(result -> result.observationCode() + "=" + result.status().name())
            .sorted()
            .toList();
    String stableSummary =
        String.join(
            "|",
            run.scenarioCode(),
            run.labRunId(),
            run.status().name(),
            String.join(",", run.executionRefs()),
            String.join(",", statuses));
    try {
      MessageDigest sha256 = MessageDigest.getInstance("SHA-256");
      return HexFormat.of()
          .formatHex(sha256.digest(stableSummary.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException unavailable) {
      throw new IllegalStateException("SHA-256 is required for failure lab evidence", unavailable);
    }
  }
}
