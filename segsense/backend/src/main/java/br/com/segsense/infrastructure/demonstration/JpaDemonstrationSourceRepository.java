package br.com.segsense.infrastructure.demonstration;

import br.com.segsense.application.demonstration.DemonstrationSourceRepository;
import br.com.segsense.domain.demonstration.DemonstrationSource;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class JpaDemonstrationSourceRepository implements DemonstrationSourceRepository {

  private final DemonstrationSourceSpringRepository sources;

  public JpaDemonstrationSourceRepository(DemonstrationSourceSpringRepository sources) {
    this.sources = sources;
  }

  @Override
  public List<DemonstrationSource> listAll() {
    return sources.findAllByOrderBySourceKeyAsc().stream().map(this::toDomain).toList();
  }

  @Override
  public Optional<DemonstrationSource> findById(UUID id) {
    return sources.findById(id).map(this::toDomain);
  }

  @Override
  public Optional<DemonstrationSource> findByKey(String key) {
    return sources.findBySourceKey(key).map(this::toDomain);
  }

  private DemonstrationSource toDomain(DemonstrationSourceJpaEntity entity) {
    return new DemonstrationSource(
        entity.getId(),
        entity.getSourceKey(),
        entity.getUrl(),
        entity.getConsultedOn(),
        entity.getAccessKind(),
        entity.getVerificationStatus(),
        entity.getSummary());
  }
}
