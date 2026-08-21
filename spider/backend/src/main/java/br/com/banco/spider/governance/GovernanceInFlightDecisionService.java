package br.com.banco.spider.governance;

import br.com.banco.spider.governance.port.GovernanceRevocationRegistryPort;
import br.com.banco.spider.execution.domain.ExecutionState;
import java.util.Objects;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class GovernanceInFlightDecisionService {

  private static final Logger log = LoggerFactory.getLogger(GovernanceInFlightDecisionService.class);

  private final GovernanceRevocationRegistryPort revocationRegistry;
  private final boolean checkEnabled;
  private final RevokedSnapshotInFlightPolicy revokedPolicy;

  public GovernanceInFlightDecisionService(
      GovernanceRevocationRegistryPort revocationRegistry,
      @Value("${spider.governance.in-flight-revocation-check.enabled:true}") boolean checkEnabled,
      @Value("${spider.governance.revoked-in-flight-policy:STOP_BEFORE_NEXT_EXTERNAL_EFFECT}")
          String revokedPolicy) {
    this.revocationRegistry = revocationRegistry;
    this.checkEnabled = checkEnabled;
    this.revokedPolicy = RevokedSnapshotInFlightPolicy.valueOf(revokedPolicy.trim());
  }

  public GovernanceInFlightDecision decide(
      GovernanceExecutionReference ref,
      GovernedEffectType effectType,
      ExecutionState currentState) {
    Objects.requireNonNull(ref, "ref");
    Objects.requireNonNull(effectType, "effectType");

    if (!checkEnabled) {
      return GovernanceInFlightDecision.ALLOW_FIXED_SNAPSHOT;
    }

    boolean revoked = revocationRegistry.isSnapshotRevoked(ref.snapshotId());
    if (!revoked) {
      log.info(
          "event=revocation_decision outcome={} effectType={}",
          GovernanceInFlightDecision.ALLOW_FIXED_SNAPSHOT,
          effectType);
      return GovernanceInFlightDecision.ALLOW_FIXED_SNAPSHOT;
    }

    if (currentState != null
        && (currentState == ExecutionState.SUCCEEDED
            || currentState == ExecutionState.FAILED
            || currentState == ExecutionState.TIMED_OUT
            || currentState == ExecutionState.CANCELLED)) {
      return GovernanceInFlightDecision.ALLOW_NON_EFFECTING_STATE_TRANSITION;
    }

    GovernanceInFlightDecision decision =
        switch (revokedPolicy) {
          case ALLOW_ALREADY_MATERIALIZED ->
              GovernanceInFlightDecision.ALLOW_NON_EFFECTING_STATE_TRANSITION;
          case REQUIRE_MANUAL_DECISION -> GovernanceInFlightDecision.REQUIRE_MANUAL_REVIEW;
          case STOP_BEFORE_NEXT_EXTERNAL_EFFECT -> GovernanceInFlightDecision.STOP_BEFORE_EFFECT;
        };

    log.info(
        "event=revocation_decision outcome={} effectType={} reasonCode=SNAPSHOT_REVOKED",
        decision,
        effectType);
    return decision;
  }

  public boolean allowsExternalEffect(GovernanceInFlightDecision decision) {
    return decision == GovernanceInFlightDecision.ALLOW_FIXED_SNAPSHOT;
  }
}
