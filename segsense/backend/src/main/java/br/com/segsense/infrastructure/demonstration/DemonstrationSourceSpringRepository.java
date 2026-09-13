package br.com.segsense.infrastructure.demonstration;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface DemonstrationSourceSpringRepository extends JpaRepository<DemonstrationSourceJpaEntity, UUID> {

  List<DemonstrationSourceJpaEntity> findAllByOrderBySourceKeyAsc();

  Optional<DemonstrationSourceJpaEntity> findBySourceKey(String sourceKey);
}
