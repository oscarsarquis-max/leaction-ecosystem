package br.com.banco.spider.governance.port;

import br.com.banco.spider.governance.ExecutionGovernanceFixation;
import java.util.Optional;

public interface ExecutionGovernanceFixationStorePort {
  void insert(ExecutionGovernanceFixation fixation);

  Optional<ExecutionGovernanceFixation> findByExecutionId(String executionId);
}
