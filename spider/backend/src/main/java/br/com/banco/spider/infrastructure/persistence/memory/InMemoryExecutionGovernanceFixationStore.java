package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.governance.ExecutionGovernanceFixation;
import br.com.banco.spider.governance.port.ExecutionGovernanceFixationStorePort;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryExecutionGovernanceFixationStore
    implements ExecutionGovernanceFixationStorePort {

  private final Map<String, ExecutionGovernanceFixation> byExecution = new ConcurrentHashMap<>();

  @Override
  public void insert(ExecutionGovernanceFixation fixation) {
    ExecutionGovernanceFixation previous =
        byExecution.putIfAbsent(fixation.executionId(), fixation);
    if (previous != null
        && (!previous.snapshotId().equals(fixation.snapshotId())
            || !previous.bundleDigest().equals(fixation.bundleDigest())
            || previous.activationSequence() != fixation.activationSequence())) {
      throw new IllegalStateException("FIXATION_CONFLICT");
    }
  }

  @Override
  public Optional<ExecutionGovernanceFixation> findByExecutionId(String executionId) {
    return Optional.ofNullable(byExecution.get(executionId));
  }
}
