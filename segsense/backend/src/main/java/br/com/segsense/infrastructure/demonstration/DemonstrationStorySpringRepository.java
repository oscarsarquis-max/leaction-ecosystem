package br.com.segsense.infrastructure.demonstration;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface DemonstrationStorySpringRepository extends JpaRepository<DemonstrationStoryJpaEntity, UUID> {

  boolean existsByStoryKey(String storyKey);

  Optional<DemonstrationStoryJpaEntity> findByStoryKey(String storyKey);

  List<DemonstrationStoryJpaEntity> findAllByOrderByCreatedAtAsc();
}
