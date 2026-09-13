package br.com.segsense.infrastructure.demonstration;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface DemonstrationRevisionSpringRepository
    extends JpaRepository<DemonstrationRevisionJpaEntity, UUID> {

  Optional<DemonstrationRevisionJpaEntity> findByStoryIdAndRevisionNumber(
      UUID storyId, Integer revisionNumber);
}
