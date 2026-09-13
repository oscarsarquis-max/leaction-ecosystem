package br.com.segsense.infrastructure.demonstration;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface DemonstrationClaimSpringRepository extends JpaRepository<DemonstrationClaimJpaEntity, UUID> {

  List<DemonstrationClaimJpaEntity> findByStoryIdAndRevisionNumberOrderByPositionAsc(
      UUID storyId, Integer revisionNumber);

  void deleteByStoryIdAndRevisionNumber(UUID storyId, Integer revisionNumber);
}
