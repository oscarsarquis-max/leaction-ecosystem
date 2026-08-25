package br.com.banco.spider.operational.failurelab;

import java.util.List;
import java.util.Optional;

/** Porta de persistência das execuções controladas e de suas evidências. */
public interface FailureLabRunStorePort {

  void save(FailureLabRun run);

  Optional<FailureLabRun> findById(String labRunId);

  List<FailureLabRun> listRecent(int limit);

  void saveEvidence(FailureLabEvidenceBundle bundle);

  Optional<FailureLabEvidenceBundle> findEvidenceByRunId(String labRunId);
}
