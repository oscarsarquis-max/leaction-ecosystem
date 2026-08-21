package br.com.banco.spider.execution.signal;

import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.governance.GovernanceExecutionReference;
import br.com.banco.spider.governance.GovernanceResolutionContext;
import java.time.Duration;
import java.util.List;
import java.util.Objects;

public record ExternalSignalIngressContext(
    String waitId,
    String executionId,
    GovernanceExecutionReference governanceRef,
    String historicalSnapshotId,
    ExternalSignalDefinition signalDefinition,
    String integrityProfileRef,
    String authnProfileRef,
    String authzPolicyRef,
    String inputMappingRef,
    String expectedContractRef,
    List<String> allowedEventTypes,
    int maximumPayloadBytes,
    Duration acceptedClockSkew,
    LateSignalPolicy lateSignalPolicy,
    GovernanceResolutionContext resolutionContext) {

  public ExternalSignalIngressContext {
    Objects.requireNonNull(waitId, "waitId");
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(governanceRef, "governanceRef");
    Objects.requireNonNull(historicalSnapshotId, "historicalSnapshotId");
    Objects.requireNonNull(signalDefinition, "signalDefinition");
    Objects.requireNonNull(integrityProfileRef, "integrityProfileRef");
    Objects.requireNonNull(expectedContractRef, "expectedContractRef");
    allowedEventTypes = allowedEventTypes == null ? List.of() : List.copyOf(allowedEventTypes);
    Objects.requireNonNull(lateSignalPolicy, "lateSignalPolicy");
    Objects.requireNonNull(resolutionContext, "resolutionContext");
  }

  public static ExternalSignalIngressContext from(
      ExecutionWaitRecord wait,
      GovernanceExecutionReference ref,
      GovernanceResolutionContext ctx,
      ExternalSignalDefinition def) {
    return new ExternalSignalIngressContext(
        wait.waitId(),
        wait.executionId(),
        ref,
        ctx.snapshotId(),
        def,
        def.integrityProfileRef(),
        def.authenticationProfileRef(),
        def.authorizationPolicyRef(),
        def.inputMappingRef(),
        def.contractRef(),
        def.allowedEventTypes(),
        def.maximumPayloadBytes(),
        def.acceptedClockSkew(),
        def.lateSignalPolicy(),
        ctx);
  }
}
