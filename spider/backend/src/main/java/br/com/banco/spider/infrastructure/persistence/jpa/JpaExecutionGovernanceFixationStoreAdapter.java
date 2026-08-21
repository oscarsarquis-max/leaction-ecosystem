package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.governance.ExecutionGovernanceFixation;
import br.com.banco.spider.governance.GovernanceMode;
import br.com.banco.spider.governance.port.ExecutionGovernanceFixationStorePort;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionGovernanceFixationEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.ExecutionGovernanceFixationJpaRepository;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@Primary
@ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
public class JpaExecutionGovernanceFixationStoreAdapter
    implements ExecutionGovernanceFixationStorePort {

  private final ExecutionGovernanceFixationJpaRepository repo;

  public JpaExecutionGovernanceFixationStoreAdapter(ExecutionGovernanceFixationJpaRepository repo) {
    this.repo = repo;
  }

  @Override
  @Transactional
  public void insert(ExecutionGovernanceFixation fixation) {
    Optional<ExecutionGovernanceFixationEntity> existing = repo.findById(fixation.executionId());
    if (existing.isPresent()) {
      ExecutionGovernanceFixation current = toModel(existing.get());
      if (!same(current, fixation)) {
        throw new IllegalStateException("FIXATION_CONFLICT");
      }
      return;
    }
    repo.save(toEntity(fixation));
  }

  @Override
  @Transactional(readOnly = true)
  public Optional<ExecutionGovernanceFixation> findByExecutionId(String executionId) {
    return repo.findById(executionId).map(JpaExecutionGovernanceFixationStoreAdapter::toModel);
  }

  private static boolean same(ExecutionGovernanceFixation a, ExecutionGovernanceFixation b) {
    return a.snapshotId().equals(b.snapshotId())
        && a.bundleDigest().equals(b.bundleDigest())
        && a.snapshotDigest().equals(b.snapshotDigest())
        && a.activationSequence() == b.activationSequence();
  }

  private static ExecutionGovernanceFixationEntity toEntity(ExecutionGovernanceFixation f) {
    ExecutionGovernanceFixationEntity e = new ExecutionGovernanceFixationEntity();
    e.setExecutionId(f.executionId());
    e.setGovernanceMode(f.governanceMode());
    e.setGovernanceScope(f.governanceScope());
    e.setSnapshotId(f.snapshotId());
    e.setBundleCode(f.bundleCode());
    e.setBundleVersion(f.bundleVersion());
    e.setBundleDigest(f.bundleDigest());
    e.setSnapshotDigest(f.snapshotDigest());
    e.setActivationSequence(f.activationSequence());
    e.setFixedAt(f.fixedAt());
    return e;
  }

  private static ExecutionGovernanceFixation toModel(ExecutionGovernanceFixationEntity e) {
    return new ExecutionGovernanceFixation(
        e.getExecutionId(),
        e.getGovernanceMode() == null ? GovernanceMode.CONTROL_PLANE : e.getGovernanceMode(),
        e.getGovernanceScope(),
        e.getSnapshotId(),
        e.getBundleCode(),
        e.getBundleVersion(),
        e.getBundleDigest(),
        e.getSnapshotDigest(),
        e.getActivationSequence(),
        e.getFixedAt());
  }
}
